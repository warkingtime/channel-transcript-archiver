import re
import sys
from datetime import datetime


def parse_time(time_str: str) -> float:
    time_obj = datetime.strptime(time_str.strip().replace(",", "."), "%H:%M:%S.%f")
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second + time_obj.microsecond / 1000000


def find_long_blocks(srt_path: str, min_duration: float = 5.0) -> None:
    with open(srt_path, encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 3:
            continue

        time_match = re.search(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", lines[1])
        if not time_match:
            continue

        start = parse_time(time_match.group(1))
        end = parse_time(time_match.group(2))
        duration = end - start

        if duration > min_duration:
            print(f"[{duration:.2f}s] {lines[2:]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 find_long_blocks.py <srt_file>")
        sys.exit(1)
    find_long_blocks(sys.argv[1])
