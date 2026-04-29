import os
from pathlib import Path
import logging
from src.extract import cleanup_trailing_whitespace, finalize_channel_update

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

def fix_all_channels():
    channels_dir = Path("channels")
    if not channels_dir.exists():
        log.error("Channels directory not found.")
        return

    for channel in channels_dir.iterdir():
        if channel.is_dir():
            log.info(f"\nProcessing channel: {channel.name}")
            cleanup_trailing_whitespace(channel)
            # Finalize to update reports with new filenames
            finalize_channel_update(channel)

if __name__ == "__main__":
    fix_all_channels()
