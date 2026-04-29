import glob
import json
import os
import sys


def populate_archive(channel_dir: str) -> None:
    archive_file = os.path.join(channel_dir, "archive.txt")
    data_dir = os.path.join(channel_dir, "data")
    existing_ids: set[str] = set()

    if os.path.exists(archive_file):
        with open(archive_file) as f:
            for line in f:
                if line.startswith("youtube "):
                    existing_ids.add(line.split(" ")[1].strip())

    print(f"Scanning {data_dir} for existing video IDs...")
    info_files = glob.glob(os.path.join(data_dir, "**", "*.info.json"), recursive=True)

    new_ids = 0
    with open(archive_file, "a") as f:
        for info_file in info_files:
            try:
                with open(info_file) as jf:
                    data = json.load(jf)
                    v_id = data.get("id")
                    if v_id and v_id not in existing_ids:
                        f.write(f"youtube {v_id}\n")
                        existing_ids.add(v_id)
                        new_ids += 1
            except Exception:
                pass

    print(f"Added {new_ids} IDs to {archive_file}. Total unique videos: {len(existing_ids)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 populate_archive.py <channel_dir>")
        sys.exit(1)
    populate_archive(sys.argv[1])
