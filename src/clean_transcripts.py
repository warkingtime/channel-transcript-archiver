import argparse
import glob
import os
import re
from datetime import datetime
from typing import Any

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def parse_time(time_str: str) -> float:
    """Converts SRT time format (HH:MM:SS,ms) to total seconds."""
    time_obj = datetime.strptime(time_str.strip().replace(",", "."), "%H:%M:%S.%f")
    return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second + time_obj.microsecond / 1000000


def clean_srt(srt_path: str, config: dict[str, Any] | None = None) -> dict[str, int] | None:
    if not os.path.exists(srt_path):
        return None

    with open(srt_path, encoding="utf-8") as f:
        data = f.read()

    blocks = re.split(r"\n\s*\n(?=\d+\n\d{2}:\d{2}:\d{2})", data.strip())
    if len(blocks) < 2:
        blocks = re.split(r"\n+(?=\d+\n\d{2}:\d{2}:\d{2})", data.strip())

    clean_lines: list[str] = []
    last_block_text: set[str] = set()
    last_end_time = 0.0
    gap_threshold = 3.0

    stats = {"gap_cuts": 0, "speaker_cuts": 0}
    has_speaker_marks = ">>" in data
    current_speaker: str | None = None

    if has_speaker_marks and config and config.get("uses_dual_speaker_heuristic"):
        full_content_normalized = re.sub(r"[^a-z0-9\s]", "", data.lower())

        a_name = config.get("speaker_a")
        b_name = config.get("speaker_b")
        a_strings = config.get("speaker_a_strings", [])
        b_strings = config.get("speaker_b_strings", [])

        first_a = -1
        for s in a_strings:
            s_norm = re.sub(r"[^a-z0-9\s]", "", s.lower())
            match = re.search(re.escape(s_norm), full_content_normalized)
            if match and (first_a == -1 or match.start() < first_a):
                first_a = match.start()

        first_b = -1
        for s in b_strings:
            s_norm = re.sub(r"[^a-z0-9\s]", "", s.lower())
            match = re.search(re.escape(s_norm), full_content_normalized)
            if match and (first_b == -1 or match.start() < first_b):
                first_b = match.start()

        if first_a != -1 and (first_b == -1 or first_a < first_b):
            current_speaker = a_name
        elif first_b != -1 and (first_a == -1 or first_b < first_a):
            current_speaker = b_name

    current_blob_start: float | None = None
    current_blob_text: list[str] = []

    def switch_speaker() -> None:
        nonlocal current_speaker
        if not (config and config.get("uses_dual_speaker_heuristic")):
            return
        a_name = str(config.get("speaker_a", "SPEAKER_A"))
        b_name = str(config.get("speaker_b", "SPEAKER_B"))
        if current_speaker == a_name:
            current_speaker = b_name
        elif current_speaker == b_name:
            current_speaker = a_name

    def flush_blob(end_time: float, pause_after: float | None = None) -> None:
        nonlocal current_blob_start
        if current_blob_text:
            text = " ".join(current_blob_text).strip()
            if text:
                duration = end_time - (current_blob_start or 0.0)
                speaker_prefix = f"{current_speaker}: " if current_speaker else ""
                clean_lines.append(f"({duration:.1f}s) {speaker_prefix}{text}\n\n")
            current_blob_text.clear()
        if pause_after is not None and pause_after >= gap_threshold:
            clean_lines.append(f"({pause_after:.1f}s) [pause]\n\n")
        current_blob_start = None

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 3:
            continue
        time_match = re.search(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", lines[1])
        if not time_match:
            continue
        start_time = parse_time(time_match.group(1))
        end_time = parse_time(time_match.group(2))
        if current_blob_start is None:
            current_blob_start = start_time
        gap = start_time - last_end_time if last_end_time > 0 else 0.0
        if gap >= gap_threshold:
            flush_blob(last_end_time, pause_after=gap)
            stats["gap_cuts"] += 1
            current_blob_start = start_time
        text_lines = lines[2:]
        for t in text_lines:
            if t not in last_block_text:
                if ">>" in t:
                    gap_at_speaker = start_time - last_end_time if last_end_time > 0 else 0.0
                    flush_blob(
                        last_end_time if last_end_time > 0 else start_time,
                        pause_after=gap_at_speaker if gap_at_speaker >= gap_threshold else None,
                    )
                    if current_speaker:
                        switch_speaker()
                    stats["speaker_cuts"] += 1
                    current_blob_start = start_time
                if t.strip():
                    current_blob_text.append(t.strip())
        last_block_text = set(text_lines)
        last_end_time = end_time

    flush_blob(last_end_time)
    full_text = "".join(clean_lines).strip()
    if current_speaker and config:
        a_name = config.get("speaker_a", "SPEAKER_A")
        b_name = config.get("speaker_b", "SPEAKER_B")
        a_strings = config.get("speaker_a_strings", [])
        b_strings = config.get("speaker_b_strings", [])
        note = (
            f"[Note: Speaker identification is based on a heuristic "
            f"({a_name}: {a_strings}, {b_name}: {b_strings}) and may be inaccurate.]\n\n"
        )
        full_text = note + full_text

    txt_path = srt_path.replace(".srt", ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    return stats


def run_cleaner(channel_dir: str, force: bool = False) -> None:
    data_dir = os.path.join(channel_dir, "data")
    config_path = os.path.join(channel_dir, "config.toml")

    config: dict[str, Any] | None = None
    if os.path.exists(config_path) and tomllib:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
            print(f"Loaded config from {config_path}")

    srt_files = glob.glob(os.path.join(data_dir, "**", "*.srt"), recursive=True)
    if not srt_files:
        print(f"No .srt files found in {data_dir}.")
        return

    total_stats = {"gap_cuts": 0, "speaker_cuts": 0}
    print(f"Cleaning files in {data_dir}...")

    files_to_process = []
    for srt in srt_files:
        txt_path = srt.replace(".srt", ".txt")
        if force or not os.path.exists(txt_path):
            files_to_process.append(srt)

    if not files_to_process:
        print("No new files to process. Use --force to re-clean everything.")
        return

    iterator = tqdm(files_to_process, desc="Cleaning") if tqdm else files_to_process

    for srt in iterator:
        stats = clean_srt(srt, config=config)
        if stats:
            for k in total_stats:
                total_stats[k] += stats[k]

    print(f"\nSummary of cuts: Silence: {total_stats['gap_cuts']}, Speakers: {total_stats['speaker_cuts']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean YouTube transcripts.")
    parser.add_argument("channel_dir", help="Path to the channel directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing cleaned transcripts.")
    args = parser.parse_args()

    run_cleaner(args.channel_dir, force=args.force)


if __name__ == "__main__":
    main()
