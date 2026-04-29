import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from .extract import get_channel_source


def list_channels() -> None:
    """Lists all currently synced channels and their metadata."""
    channels_dir = Path("channels")
    if not channels_dir.exists() or not channels_dir.is_dir():
        print("No channels found.")
        return

    channels: list[dict[str, Any]] = []
    for item in channels_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            channel_info: dict[str, Any] = {
                "name": str(item.name),
                "url": "Unknown",
                "type": "Unknown",
                "videos": 0,
                "speakers": "N/A",
                "last_post": "N/A",
            }

            # Try to get info from config.toml
            config_path = item / "config.toml"
            if config_path.exists() and tomllib:
                try:
                    with open(config_path, "rb") as f:
                        config_data = tomllib.load(f)
                        url = config_data.get("url")
                        if isinstance(url, str):
                            channel_info["url"] = url
                            channel_info["type"] = get_channel_source(url).capitalize()

                        speaker_a = config_data.get("speaker_a")
                        speaker_b = config_data.get("speaker_b")
                        if isinstance(speaker_a, str) and isinstance(speaker_b, str):
                            channel_info["speakers"] = f"{speaker_a} & {speaker_b}"
                        elif isinstance(speaker_a, str):
                            channel_info["speakers"] = speaker_a
                except Exception:
                    pass

            # Fallback for URL from README.md if config failed
            if channel_info["url"] == "Unknown":
                readme_path = item / "README.md"
                if readme_path.exists():
                    try:
                        content = readme_path.read_text()
                        import re

                        match = re.search(r"transcripts for: (https?://\S+)", content)
                        if match:
                            url = match.group(1)
                            channel_info["url"] = url
                            channel_info["type"] = get_channel_source(url).capitalize()
                    except Exception:
                        pass

            # Count videos and find last post date in data/
            data_dir = item / "data"
            if data_dir.exists() and data_dir.is_dir():
                video_dirs = [d.name for d in data_dir.iterdir() if d.is_dir()]
                channel_info["videos"] = len(video_dirs)
                if video_dirs:
                    import re

                    dates = []
                    for d_name in video_dirs:
                        date_match = re.match(r"^(\d{4}-?\d{2}-?\d{2})", d_name)
                        if date_match:
                            dates.append(date_match.group(1).replace("-", ""))

                    if dates:
                        dates.sort()
                        last_date = dates[-1]
                        # Normalize to YYYY-MM-DD
                        if len(last_date) == 8:
                            channel_info["last_post"] = f"{last_date[:4]}-{last_date[4:6]}-{last_date[6:]}"
                        else:
                            channel_info["last_post"] = last_date

            channels.append(channel_info)

    if not channels:
        print("No channels found.")
        return

    # Sort channels by name
    channels.sort(key=lambda x: str(x["name"]).lower())

    # Calculate column widths
    name_w = max(len("Channel Name"), max(len(str(c["name"])) for c in channels)) + 2
    type_w = max(len("Type"), max(len(str(c["type"])) for c in channels)) + 2
    videos_w = max(len("Videos"), max(len(str(c["videos"])) for c in channels)) + 2
    speakers_w = max(len("Speakers"), max(len(str(c["speakers"])) for c in channels)) + 2
    last_post_w = max(len("Last Post"), max(len(str(c["last_post"])) for c in channels)) + 2

    # Print table with clean formatting
    header = (
        f"{'Channel Name':<{name_w}} | "
        f"{'Type':<{type_w}} | "
        f"{'Videos':<{videos_w}} | "
        f"{'Last Post':<{last_post_w}} | "
        f"{'Speakers':<{speakers_w}} | "
        f"URL"
    )
    separator = "-" * len(header)
    if len(header) < 120:
        separator = "-" * 120

    print(f"\n{header}")
    print(separator)

    for c in channels:
        print(
            f"{str(c['name']):<{name_w}} | "
            f"{str(c['type']):<{type_w}} | "
            f"{str(c['videos']):<{videos_w}} | "
            f"{str(c['last_post']):<{last_post_w}} | "
            f"{str(c['speakers']):<{speakers_w}} | "
            f"{str(c['url'])}"
        )
    print()


if __name__ == "__main__":
    list_channels()
