import os
import re
from pathlib import Path

def update_toml_files():
    channels_dir = Path("channels")
    if not channels_dir.is_dir():
        print("No channels directory found.")
        return

    for channel_path in channels_dir.iterdir():
        if not channel_path.is_dir():
            continue
        
        config_path = channel_path / "config.toml"
        readme_path = channel_path / "README.md"
        
        if not config_path.exists():
            continue
            
        print(f"Processing {channel_path.name}...")
        
        # Read current config
        config_content = config_path.read_text()
        if 'url =' in config_content:
            print(f"  - already has URL, skipping.")
            continue
            
        # Try to find URL in README
        url = None
        if readme_path.exists():
            readme_content = readme_path.read_text()
            # More flexible search for URLs in the description line
            match = re.search(r"transcripts for.*: (https?://\S+)", readme_content)
            if match:
                url = match.group(1).strip()
        
        if url:
            # Prepend URL to config.toml
            new_content = f'url = "{url}"\n' + config_content
            config_path.write_text(new_content)
            print(f"  - Updated with URL: {url}")
        else:
            print(f"  - Could not find URL in README for {channel_path.name}")

if __name__ == "__main__":
    update_toml_files()
