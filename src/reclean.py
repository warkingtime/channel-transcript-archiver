import argparse
import logging
import sys
from pathlib import Path

from .clean_transcripts import run_cleaner
from .format_and_summarize import (
    format_json_files,
    generate_transcripts_list,
    get_video_map,
    summarize_playlists,
)
from .populate_archive import populate_archive
from .remove_duplicates import (
    find_cross_folder_duplicates,
    remove_intra_folder_duplicates,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def reclean(folder_name: str) -> None:
    channel_dir = Path("channels") / folder_name
    if not channel_dir.exists():
        log.error(f"Error: Directory {channel_dir} does not exist.")
        sys.exit(1)

    log.info(f"Starting local re-cleanup for: {folder_name}")

    # Update archive.txt from local files
    log.info("Updating archive.txt...")
    populate_archive(str(channel_dir))

    # Remove duplicate files
    log.info("Deduplicating files...")
    remove_intra_folder_duplicates(str(channel_dir))
    find_cross_folder_duplicates(str(channel_dir))

    # Clean transcripts (forced re-clean)
    log.info("Re-cleaning transcripts...")
    run_cleaner(str(channel_dir), force=True)

    # Format JSONs and summarize playlists
    log.info("Updating reports and formatting JSON files...")
    format_json_files(str(channel_dir))
    v_map = get_video_map(str(channel_dir))
    summarize_playlists(v_map, str(channel_dir))
    generate_transcripts_list(v_map, str(channel_dir))

    log.info(f"Local re-cleanup complete for {folder_name}!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Re-cleanup Script")
    parser.add_argument("name", help="Folder name of the channel to re-clean")
    args = parser.parse_args()
    reclean(args.name)


if __name__ == "__main__":
    main()
