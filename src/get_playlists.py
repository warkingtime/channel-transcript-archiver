import json
import os
import subprocess
from typing import Any

CHANNEL_URL = "https://www.youtube.com/@ExampleChannel/playlists"
OUTPUT_DIR = "playlists"


def get_playlist_data(channel_url: str = CHANNEL_URL, output_dir: str = OUTPUT_DIR) -> None:
    os.makedirs(output_dir, exist_ok=True)

    print("Fetching playlist list...")
    cmd = [
        "yt-dlp",
        "--get-id",
        "--flat-playlist",
        channel_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    playlist_ids = result.stdout.strip().split("\n")

    for p_id in playlist_ids:
        if not p_id:
            continue
        url = f"https://www.youtube.com/playlist?list={p_id}"
        print(f"Fetching metadata for playlist: {p_id}")

        cmd_meta = [
            "yt-dlp",
            "--dump-single-json",
            "--flat-playlist",
            url,
        ]
        result_meta = subprocess.run(cmd_meta, capture_output=True, text=True, check=False)
        if result_meta.returncode == 0:
            try:
                data: dict[str, Any] = json.loads(result_meta.stdout)
                title = str(data.get("title", p_id))
                safe_title = "".join(c for c in title if c.isalnum() or c in (" ", ".", "_")).strip()
                output_path = os.path.join(output_dir, f"{safe_title}.info.json")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                print(f"  Saved metadata for: {title}")
            except Exception as e:
                print(f"  Error parsing JSON for {p_id}: {e}")
        else:
            print(f"  Error fetching metadata for {p_id}")


if __name__ == "__main__":
    get_playlist_data()
