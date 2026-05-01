import argparse
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from .browser import get_cookie_args
from .clean_transcripts import run_cleaner
from .format_and_summarize import (
    format_json_files,
    generate_transcripts_list,
    get_video_map,
    summarize_playlists,
)
from .get_patreon_collections import download_patreon_collections
from .populate_archive import populate_archive
from .remove_duplicates import (
    find_cross_folder_duplicates,
    remove_intra_folder_duplicates,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def sanitize_folder_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


def extract_folder_name(url: str) -> str:
    """Extracts a default folder name from a YouTube or Patreon URL."""
    if "@" in url:
        return url.split("@")[-1].split("/")[0]
    elif "/channel/" in url:
        return url.split("/channel/")[-1].split("/")[0]
    elif "/c/" in url:
        return url.split("/c/")[-1].split("/")[0]
    elif "patreon.com" in url:
        # Handle Patreon URL patterns: https://www.patreon.com/c/SimoneAndMalcolmCollins/
        return url.rstrip("/").split("/")[-1]
    return "channel"


def get_channel_source(url: str) -> str:
    if "patreon.com" in url:
        return "patreon"
    return "youtube"


def resolve_unique_folder_name(proposed_name: str, url: str) -> str:
    """Resolves a unique folder name in the channels/ directory.

    If the proposed name exists and points to a different URL, it appends the source
    (e.g. ' (youtube)') and then numbers if needed.
    """
    base_dir = Path("channels")
    proposed_name = sanitize_folder_name(proposed_name)
    target_dir = base_dir / proposed_name

    def is_same_channel(path: Path, target_url: str) -> bool:
        readme_path = path / "README.md"
        if readme_path.exists():
            return target_url in readme_path.read_text()
        return False

    if not target_dir.exists() or is_same_channel(target_dir, url):
        return proposed_name

    # Collision! Try adding source
    source = get_channel_source(url)
    sourced_name = f"{proposed_name} ({source})"
    target_dir = base_dir / sourced_name

    if not target_dir.exists() or is_same_channel(target_dir, url):
        return sourced_name

    # Still colliding! Start adding numbers
    counter = 1
    while True:
        numbered_name = f"{sourced_name} {counter}"
        target_dir = base_dir / numbered_name
        if not target_dir.exists() or is_same_channel(target_dir, url):
            return numbered_name
        counter += 1


def rename_descriptions(channel_dir: Path) -> None:
    """Renames all .description files to .description.txt for better compatibility."""
    desc_files = list(channel_dir.glob("data/**/*.description"))
    if desc_files:
        log.info(f"Renaming {len(desc_files)} description files to .txt...")
        for f in desc_files:
            f.rename(f.with_suffix(".description.txt"))


def clean_title_whitespace(name: str) -> str:
    """Replaces all whitespace types with standard space and strips edges and spaces before dots."""
    # Replace all whitespace (including NBSP, tabs, etc.) with standard space
    name = re.sub(r"\s+", " ", name)
    # Remove spaces before dots
    name = re.sub(r" \.", ".", name)
    return name.strip()


def cleanup_trailing_whitespace(channel_dir: Path) -> None:
    """Trims trailing whitespace from all files and directories in the channel directory."""
    log.info(f"Trimming trailing whitespace in {channel_dir}...")
    # Use topdown=False to ensure we rename children before parents
    for root, dirs, files in os.walk(channel_dir, topdown=False):
        # Rename files
        for name in files:
            p = Path(root) / name
            new_name = name

            # Handle our specific multi-part extensions
            found_ext = False
            for ext in [".info.json", ".en.srt", ".en.txt", ".description.txt", ".description"]:
                if name.endswith(ext):
                    base = name[: -len(ext)]
                    new_name = clean_title_whitespace(base) + ext
                    found_ext = True
                    break

            if not found_ext:
                # Fallback for single extensions or no extension
                stem = clean_title_whitespace(p.stem)
                suffix = p.suffix
                new_name = stem + suffix

            if new_name != name:
                new_p = Path(root) / new_name
                if not new_p.exists():
                    log.info(f"Renaming file: '{name}' -> '{new_name}'")
                    p.rename(new_p)
                else:
                    log.warning(f"Could not rename '{name}' to '{new_name}': target exists")

        # Rename directories
        for name in dirs:
            p = Path(root) / name
            new_name = clean_title_whitespace(name)
            if new_name != name:
                new_p = Path(root) / new_name
                if not new_p.exists():
                    log.info(f"Renaming directory: '{name}' -> '{new_name}'")
                    p.rename(new_p)
                else:
                    log.warning(f"Could not rename directory '{name}' to '{new_name}': target exists")


def setup_channel_directory(channel_dir: Path, channel_url: str) -> None:
    """Sets up the channel directory with README.md and config.toml if they don't exist."""
    data_dir = channel_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create README.md if it doesn't exist
    readme_path = channel_dir / "README.md"
    if not readme_path.exists():
        log.info(f"Creating README.md in {channel_dir}...")
        source_type = "Patreon" if "patreon.com" in channel_url else "YouTube"
        folder_name = channel_dir.name
        readme_content = f"""# 📺 {source_type} Archive: {folder_name}

This directory contains an automated archive of metadata, descriptions, and
transcripts for: {channel_url}

## 📂 Contents
- **data/**: Chronological folders for each post containing:
    - `.info.json`: Pruned metadata.
    - `.description.txt`: Original description.
    - `.en.srt`: Original subtitles.
    - `.en.txt`: Cleaned, speaker-tagged transcript.
- **playlists/**: Metadata for all playlists (if applicable).
- **archive.txt**: A record of all synced items to ensure incremental updates.
- **config.toml**: Heuristics used for speaker identification.
- **PLAYLISTS.md**: An index organized by playlist.
- **TRANSCRIPTS.md**: A chronological index of all available transcripts.

## 🔄 How to Update
To sync new content or re-process existing ones, use the [Channel Transcript Archiver](https://github.com/warkingtime/channel-transcript-archiver):

1. Install the tool.
2. Run the sync command from the project root:
   ```bash
   uv run channel-archiver sync "{channel_url}" "{folder_name}"
   ```

## 🛠️ Tooling
Generated by [warkingtime/channel-transcript-archiver](https://github.com/warkingtime/channel-transcript-archiver).
"""
        readme_path.write_text(readme_content)

    # Create default config.toml if it doesn't exist
    config_path = channel_dir / "config.toml"
    if not config_path.exists():
        log.info("Creating default config.toml...")
        config_content = f"""# Configuration for speaker identification and transcript processing
url = "{channel_url}"
uses_dual_speaker_heuristic = false

# Define speakers and identifying phrases
# The script looks for these strings (case-insensitive) to identify the speaker
speaker_a = "SPEAKER_1"
speaker_a_strings = ["hello speaker 2", "hi speaker 2"]

speaker_b = "SPEAKER_2"
speaker_b_strings = ["hello speaker 1", "hi speaker 1"]

# Pause detection threshold in seconds (default: 3.0)
# A new paragraph is started if the gap between segments exceeds this.
# pause_threshold = 3.0
"""
        config_path.write_text(config_content)


def finalize_channel_update(channel_dir: Path, force: bool = False) -> None:
    """Performs post-download tasks: renaming, deduplication, cleaning, and reporting."""
    # Rename descriptions to .txt
    rename_descriptions(channel_dir)

    # Trim trailing whitespace from filenames and directories
    cleanup_trailing_whitespace(channel_dir)

    # Deduplicate
    log.info("Deduplicating files...")
    remove_intra_folder_duplicates(str(channel_dir))
    find_cross_folder_duplicates(str(channel_dir))

    # Clean transcripts
    log.info("Cleaning transcripts...")
    run_cleaner(str(channel_dir), force=force)

    # Format and Summarize
    log.info("Updating reports and formatting JSON files...")
    format_json_files(str(channel_dir))
    v_map = get_video_map(str(channel_dir))
    summarize_playlists(v_map, str(channel_dir))
    generate_transcripts_list(v_map, str(channel_dir))


def sync_channel(
    channel_url: str,
    folder_name: str | None = None,
    force: bool = False,
    cookies_file: str | None = None,
    cookies_browser: str | None = None,
    use_cookies: bool = False,
    print_command: bool = False,
    include_comments: int | None = None,
) -> None:
    # Check if channel_url is actually a folder name
    potential_dir = Path("channels") / channel_url
    if not channel_url.startswith(("http://", "https://")) and potential_dir.is_dir():
        log.info(f"Detected folder name '{channel_url}', resolving URL...")
        folder_name = channel_url
        channel_dir = potential_dir
        found_url = None

        # 1. Try config.toml
        config_path = channel_dir / "config.toml"
        if config_path.exists() and tomllib:
            try:
                with open(config_path, "rb") as f:
                    config_data = tomllib.load(f)
                    found_url = config_data.get("url")
            except Exception:
                pass

        # 2. Try README.md fallback
        if not found_url:
            readme_path = channel_dir / "README.md"
            if readme_path.exists():
                text = readme_path.read_text()
                match = re.search(r"transcripts for: (https?://\S+)", text)
                if match:
                    found_url = match.group(1)

        if found_url:
            log.info(f"Resolved folder '{folder_name}' to URL: {found_url}")
            channel_url = found_url
        else:
            log.error(f"Could not find a URL for folder '{folder_name}'. Please provide the URL.")
            return

    if not folder_name:
        folder_name = extract_folder_name(channel_url)

    folder_name = resolve_unique_folder_name(folder_name, channel_url)
    channel_dir = Path("channels") / folder_name

    if not print_command:
        log.info(f"Syncing channel: {channel_url} into {channel_dir} (Force: {'on' if force else 'off'})")
        setup_channel_directory(channel_dir, channel_url)

        # Update archive.txt from existing files
        log.info("Updating archive.txt from local files...")
        populate_archive(str(channel_dir))

    cookie_args = get_cookie_args(
        cookies_file=cookies_file, cookies_from_browser=cookies_browser, use_cookies=use_cookies
    )

    # yt-dlp content sync
    if not print_command:
        log.info(f"Starting yt-dlp sync for {channel_url}...")
    
    yt_dlp_cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-description",
        "--write-info-json",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "en.*",
        "--convert-subs",
        "srt",
        "--ignore-errors",
        "--ignore-no-formats-error",
        "--allow-unplayable-formats",
        "--remote-components",
        "ejs:github",
        "--output",
        f"{channel_dir}/data/%(upload_date)s - %(title)s/%(title)s.%(ext)s",
        "--sleep-requests",
        "1",
        "--sleep-interval",
        "1",
    ]

    import shutil
    if shutil.which("deno"):
        yt_dlp_cmd.extend(["--js-runtime", "deno"])
    elif shutil.which("node"):
        yt_dlp_cmd.extend(["--js-runtime", "node"])

    if not force:
        yt_dlp_cmd.extend(["--download-archive", str(channel_dir / "archive.txt")])

    if include_comments:
        yt_dlp_cmd.extend(["--write-comments", "--extractor-args", f"youtube:max-comments={include_comments}"])
    yt_dlp_cmd.extend(cookie_args)
    yt_dlp_cmd.append(channel_url)

    if print_command:
        import shlex

        print(f"\n[DRY RUN] Would execute: {shlex.join(yt_dlp_cmd)}")
    else:
        subprocess.run(yt_dlp_cmd)

    # yt-dlp playlist metadata (YouTube only for now)
    if ("youtube.com" in channel_url or "youtu.be" in channel_url) and not print_command:
        log.info("Extracting playlist metadata...")
        playlists_dir = channel_dir / "playlists"
        playlists_dir.mkdir(parents=True, exist_ok=True)
        playlist_cmd = [
            "yt-dlp",
            "--write-info-json",
            "--flat-playlist",
            "--allow-unplayable-formats",
            "--output",
            f"{channel_dir}/playlists/%(title)s.%(ext)s",
        ]
        playlist_cmd.extend(cookie_args)
        playlist_cmd.append(f"{channel_url}/playlists")

        subprocess.run(playlist_cmd)

        # Remove playlists directory if it's empty
        if playlists_dir.exists() and not any(playlists_dir.iterdir()):
            playlists_dir.rmdir()
    elif print_command and ("youtube.com" in channel_url or "youtu.be" in channel_url):
        import shlex

        playlist_cmd = [
            "yt-dlp",
            "--write-info-json",
            "--flat-playlist",
            "--allow-unplayable-formats",
            "--output",
            f"{channel_dir}/playlists/%(title)s.%(ext)s",
        ]
        playlist_cmd.extend(cookie_args)
        playlist_cmd.append(f"{channel_url}/playlists")
        print(f"[DRY RUN] Would execute: {shlex.join(playlist_cmd)}")
    elif "patreon.com" in channel_url and not print_command:
        log.info("Extracting Patreon collections metadata...")
        cookies_path = cookies_file or "cookies.txt"
        # If cookies_browser is provided, we might want to extract them first,
        # but for now we assume they are in cookies.txt or .browser handled by get_cookie_args
        # Actually, get_cookie_args returns yt-dlp arguments.
        # We need a path for the requests session.
        if cookies_file:
            path = cookies_file
        elif Path("cookies.txt").exists():
            path = "cookies.txt"
        else:
            path = "cookies.txt"  # Fallback
        
        download_patreon_collections(channel_url, channel_dir, cookies_path=path)
    else:
        log.info("Skipping playlist metadata extraction (non-YouTube/Patreon URL).")

    if not print_command:
        finalize_channel_update(channel_dir, force=force)
        log.info(f"Sync complete for {folder_name}!")


def download_video(
    video_url: str,
    folder_name: str | None = None,
    force: bool = False,
    cookies_file: str | None = None,
    cookies_browser: str | None = None,
    use_cookies: bool = False,
    print_command: bool = False,
    include_comments: int | None = None,
) -> None:
    cookie_args = get_cookie_args(
        cookies_file=cookies_file, cookies_from_browser=cookies_browser, use_cookies=use_cookies
    )

    if not folder_name:
        if not print_command:
            log.info(f"Detecting uploader for {video_url}...")
        try:
            cmd = [
                "yt-dlp",
                "--print",
                "uploader_url",
                "--ignore-errors",
                "--allow-unplayable-formats",
                video_url,
            ] + cookie_args
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            uploader_url = result.stdout.strip()
            folder_name = extract_folder_name(uploader_url)
        except Exception as e:
            log.warning(f"Could not detect uploader: {e}. Using 'downloads' folder.")
            folder_name = "downloads"

    folder_name = resolve_unique_folder_name(folder_name, video_url)
    channel_dir = Path("channels") / folder_name

    if not print_command:
        log.info(f"Downloading video: {video_url} into {channel_dir}")
        setup_channel_directory(channel_dir, video_url)

    # yt-dlp content download
    if not print_command:
        log.info(f"Starting yt-dlp download for {video_url}...")
    yt_dlp_cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-description",
        "--write-info-json",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "en.*",
        "--convert-subs",
        "srt",
        "--ignore-errors",
        "--ignore-no-formats-error",
        "--no-playlist",
        "--allow-unplayable-formats",
        "--remote-components",
        "ejs:github",
        "--output",
        f"{channel_dir}/data/%(upload_date)s - %(title)s/%(title)s.%(ext)s",
    ]

    import shutil
    if shutil.which("deno"):
        yt_dlp_cmd.extend(["--js-runtime", "deno"])
    elif shutil.which("node"):
        yt_dlp_cmd.extend(["--js-runtime", "node"])

    if include_comments:
        yt_dlp_cmd.extend(["--write-comments", "--extractor-args", f"youtube:max-comments={include_comments}"])
    yt_dlp_cmd.extend(cookie_args)
    yt_dlp_cmd.append(video_url)

    if print_command:
        import shlex

        print(f"\n[DRY RUN] Would execute: {shlex.join(yt_dlp_cmd)}")
    else:
        subprocess.run(yt_dlp_cmd)

    if not print_command:
        finalize_channel_update(channel_dir, force=force)
        log.info(f"Download complete for {folder_name}!")


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Channel Transcript Archiver")
    parser.add_argument("url", help="YouTube Channel URL")
    parser.add_argument("name", nargs="?", help="Folder name for the channel")
    parser.add_argument("--force", action="store_true", help="Force re-cleaning of transcripts")
    parser.add_argument("--cookies", help="Path to cookies.txt file")
    parser.add_argument("--cookies-from-browser", help="Browser to extract cookies from")

    args = parser.parse_args()

    sync_channel(
        args.url,
        folder_name=args.name,
        force=args.force,
        cookies_file=args.cookies,
        cookies_browser=args.cookies_from_browser,
    )


if __name__ == "__main__":
    main()
