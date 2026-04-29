import re
import sys
from datetime import datetime


def parse_time(time_str: str) -> float:
    time_obj = datetime.strptime(time_str.strip().replace(",", "."), "%H:%M:%S.%f")
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second + time_obj.microsecond / 1000000


def analyze_gaps(srt_path: str) -> None:
    with open(srt_path, encoding="utf-8") as f:
        content = f.read()

    matches = re.findall(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", content)

    gaps: list[float] = []
    last_end: float | None = None
    for start_str, end_str in matches:
        start = parse_time(start_str)
        end = parse_time(end_str)
        if last_end is not None:
            gap = start - last_end
            if gap > 0:
                gaps.append(gap)
        last_end = end

    gaps.sort(reverse=True)
    print(f"Total gaps found: {len(gaps)}")
    print(f"Top 20 gaps (seconds): {gaps[:20]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_gaps.py <srt_file>")
        sys.exit(1)
    analyze_gaps(sys.argv[1])
