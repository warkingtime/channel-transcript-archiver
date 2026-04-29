import glob
import json
import os
import re
import sys
import urllib.parse
from typing import Any


def escape_markdown_table_content(text: str) -> str:
    if not text:
        return ""
    return text.replace("|", "\\|")


def format_json_files(channel_dir: str) -> None:
    print(f"Formatting and pruning JSON files in {channel_dir}...")
    json_files = glob.glob(os.path.join(channel_dir, "data/**/*.json"), recursive=True)
    json_files += glob.glob(os.path.join(channel_dir, "playlists/**/*.json"), recursive=True)
    json_files = list(set(json_files))

    keys_to_remove = [
        "formats",
        "thumbnails",
        "automatic_captions",
        "http_headers",
        "requested_subtitles",
        "_format_sort_fields",
        "downloader_options",
        "requested_formats",
    ]

    for json_file in json_files:
        if os.path.isdir(json_file):
            continue
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            for k in keys_to_remove:
                if k in data:
                    del data[k]
            if "entries" in data and isinstance(data["entries"], list):
                for entry in data["entries"]:
                    if isinstance(entry, dict):
                        for k in keys_to_remove:
                            if k in entry:
                                del entry[k]
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"  Error formatting {json_file}: {e}")


def get_video_map(channel_dir: str) -> dict[str, dict[str, str]]:
    video_map: dict[str, dict[str, str]] = {}
    data_dir = os.path.join(channel_dir, "data")
    info_files = glob.glob(os.path.join(data_dir, "**/*.info.json"), recursive=True)
    for ifile in info_files:
        try:
            with open(ifile, encoding="utf-8") as f:
                data = json.load(f)
                v_id: str | None = data.get("id")
                if v_id:
                    video_map[v_id] = {
                        "folder": os.path.dirname(ifile),
                        "upload_date": str(data.get("upload_date", "Unknown")),
                        "title": str(data.get("title", "Unknown")),
                        "url": str(data.get("webpage_url", f"https://www.youtube.com/watch?v={v_id}")),
                    }
        except Exception:
            pass
    return video_map


def format_date(date_str: str | None) -> str:
    if date_str and len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str or "Unknown"


def get_transcript_link(v_id: str, video_map: dict[str, dict[str, str]], channel_dir: str) -> str:
    if v_id not in video_map:
        return "N/A"
    folder = video_map[v_id]["folder"]
    txt_files = glob.glob(os.path.join(folder, "*.txt"))
    txt_files = [tf for tf in txt_files if not tf.endswith(".description") and not tf.endswith(".description.txt")]
    if txt_files:
        rel_path = os.path.relpath(txt_files[0], channel_dir)
        return f"[transcript]({urllib.parse.quote(rel_path)})"
    return "N/A"


def summarize_playlists(video_map: dict[str, dict[str, str]], channel_dir: str) -> None:
    playlist_files = glob.glob(os.path.join(channel_dir, "playlists/*.info.json"))
    playlists_data: list[dict[str, Any]] = []
    for pf in playlist_files:
        try:
            with open(pf, encoding="utf-8") as f:
                playlists_data.append(json.load(f))
        except Exception:
            pass
    playlists_data.sort(key=lambda x: x.get("title", "").lower())

    output_path = os.path.join(channel_dir, "PLAYLISTS.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Playlists Summary\n\n## Overview\n\n| Playlist Title | Items | Link |\n| --- | --- | --- |\n")
        for p in playlists_data:
            title = escape_markdown_table_content(p.get("title", "Unknown"))
            anchor = re.sub(r"\s+", "-", re.sub(r"[^a-z0-9\s-]", "", title.lower())).strip("-")
            count = p.get("playlist_count") or len(p.get("entries", []))
            url = p.get("webpage_url", "")
            f.write(f"| [{title}](#{anchor}) | {count} | [Source]({url}) |\n")

        for p in playlists_data:
            title = p.get("title", "Unknown")
            f.write(f"\n## {title}\n\n| Date | Title | Transcript |\n| --- | --- | --- |\n")
            for entry in p.get("entries", []):
                if not entry:
                    continue
                e_id = entry.get("id")
                if not e_id:
                    continue
                e_title = escape_markdown_table_content(entry.get("title", "Unknown"))
                e_url = entry.get("webpage_url", f"https://www.youtube.com/watch?v={e_id}")
                date = format_date(video_map[e_id]["upload_date"]) if e_id in video_map else "Unknown"
                t_link = get_transcript_link(e_id, video_map, channel_dir)
                f.write(f"| {date} | [{e_title}]({e_url}) | {t_link} |\n")


def generate_transcripts_list(video_map: dict[str, dict[str, str]], channel_dir: str) -> None:
    sorted_ids = sorted(
        video_map.keys(),
        key=lambda x: video_map[x].get("upload_date", "00000000"),
        reverse=True,
    )
    output_path = os.path.join(channel_dir, "TRANSCRIPTS.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# All Content and Transcripts\n\n| Date | Title | Transcript |\n| --- | --- | --- |\n")
        for v_id in sorted_ids:
            info = video_map[v_id]
            date = format_date(info["upload_date"])
            title = escape_markdown_table_content(info["title"])
            t_link = get_transcript_link(v_id, video_map, channel_dir)
            f.write(f"| {date} | [{title}]({info['url']}) | {t_link} |\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 format_and_summarize.py <channel_dir>")
        sys.exit(1)
    chan_dir = sys.argv[1]
    format_json_files(chan_dir)
    v_map = get_video_map(chan_dir)
    summarize_playlists(v_map, chan_dir)
    generate_transcripts_list(v_map, chan_dir)
