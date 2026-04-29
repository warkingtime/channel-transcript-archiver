import re
import sys
from datetime import datetime


def parse_time(time_str: str) -> float:
    time_obj = datetime.strptime(time_str.strip().replace(",", "."), "%H:%M:%S.%f")
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second + time_obj.microsecond / 1000000


def analyze_durations(srt_path: str) -> None:
    with open(srt_path, encoding="utf-8") as f:
        content = f.read()

    matches = re.findall(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", content)

    durations: list[float] = []
    for start_str, end_str in matches:
        start = parse_time(start_str)
        end = parse_time(end_str)
        durations.append(end - start)

    durations.sort(reverse=True)
    print(f"Total blocks: {len(durations)}")
    print(f"Top 20 durations (seconds): {durations[:20]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_durations.py <srt_file>")
        sys.exit(1)
    analyze_durations(sys.argv[1])
