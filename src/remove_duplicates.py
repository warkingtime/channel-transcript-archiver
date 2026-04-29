import glob
import os
import sys


def remove_intra_folder_duplicates(channel_dir: str) -> None:
    """Removes redundant subtitle/transcript files in the same folder."""
    data_dir = os.path.join(channel_dir, "data")
    folders = [d for d in glob.glob(os.path.join(data_dir, "*")) if os.path.isdir(d)]

    removed_count = 0
    for folder in folders:
        srts = glob.glob(os.path.join(folder, "*.srt"))
        if len(srts) > 1:
            orig_srts = [s for s in srts if ".en-orig." in s]
            standard_srts = [s for s in srts if ".en." in s and ".en-orig." not in s]

            if standard_srts and orig_srts:
                for s in orig_srts:
                    print(f"  Removing redundant {os.path.basename(s)}")
                    os.remove(s)
                    removed_count += 1
                    txt = s.replace(".srt", ".txt")
                    if os.path.exists(txt):
                        os.remove(txt)

    print(f"Removed {removed_count} redundant files.")


def find_cross_folder_duplicates(channel_dir: str) -> None:
    """Identifies potential duplicate videos in different folders."""
    data_dir = os.path.join(channel_dir, "data")
    folders = [d for d in glob.glob(os.path.join(data_dir, "*")) if os.path.isdir(d)]

    titles: dict[str, list[str]] = {}
    for folder in folders:
        basename = os.path.basename(folder)
        if " - " in basename:
            parts = basename.split(" - ", 1)
            title = parts[1]
            if title not in titles:
                titles[title] = []
            titles[title].append(folder)

    duplicates = {t: f for t, f in titles.items() if len(f) > 1}

    if duplicates:
        print("\nPotential cross-folder duplicates (same title):")
        for title, folders in duplicates.items():
            print(f"  Title: {title}")
            for f in folders:
                print(f"    - {f}")
    else:
        print("\nNo cross-folder title duplicates found.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 remove_duplicates.py <channel_dir>")
        sys.exit(1)
    chan_dir = sys.argv[1]
    print(f"Checking for duplicates in {chan_dir}...")
    remove_intra_folder_duplicates(chan_dir)
    find_cross_folder_duplicates(chan_dir)
