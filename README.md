# 📺 YouTube & Patreon Channel Transcript Archiver

A robust, generalized tool designed to archive metadata, descriptions, and intelligently cleaned transcripts from any YouTube channel or Patreon creator. This project automates the pipeline from discovery to high-quality text extraction.

> [!NOTE]
> This tool downloads existing subtitles and metadata; it does **not** use AI/TTS models to generate transcripts from audio.

---

## ✨ Features

- **🚀 Universal Sync**: Archive full YouTube channels or Patreon creator posts with a single command.
- **🧹 Smart Cleaning**: Converts messy SRT subtitles into readable text documents with intelligent pause detection.
- **🗣️ Speaker Heuristics**: Customizable speaker-tagging heuristics for two-person conversations.
- **🛡️ Secure Cookies**: Opt-in browser cookie extraction (Chrome, Brave, Firefox, etc.) for age-restricted content.
- **📂 Unique Naming**: Automatically handles folder name collisions by tagging the source (e.g., `Creator (youtube)` vs `Creator (patreon)`).
- **🗜️ Metadata Pruning**: Automatically strips large binary fields and PII from JSON metadata to save space.
- **📚 Auto-Indexing**: Generates chronological `TRANSCRIPTS.md` and `PLAYLISTS.md` indices for easy navigation.
- **🔄 Local Re-processing**: Re-clean and re-index existing data without re-downloading.

---

## 🛠️ Installation

### Prerequisites

- **Python 3.10+**
- **[uv](https://github.com/astral-sh/uv)** (High-performance Python package manager)
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/warkingtime/channel-transcript-archiver
   cd channel-transcript-archiver
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

---

## 🚀 Usage

### Unified CLI
The easiest way to use the archiver is through the `./channel-archiver` wrapper:

```bash
./channel-archiver <command> [args]
```

**Available Commands:**
- `sync`: Archive and sync a channel or Patreon creator.
- `download`: Download and clean a single video transcript.
- `reclean`: Local re-cleanup and re-indexing of an existing channel.
- `list-browsers`: List available browsers and profiles for cookie extraction.
- `cookies`: Extract fresh cookies from a browser to a static file.
- `compress`: Archive a channel directory into a compressed file (`.zip`, `.tar.xz`).

---

### Archive or Update a Channel
To start archiving a new channel or update an existing one:

```bash
# New channel (requires URL)
./channel-archiver sync <URL> [FOLDER_NAME] [--use-cookies] [--include-comments [N]]

# Update existing channel (uses folder name)
./channel-archiver sync <FOLDER_NAME> [--use-cookies] [--include-comments [N]]
```

**Examples:**
```bash
./channel-archiver sync https://www.youtube.com/@ExampleChannel ExampleChannel
./channel-archiver sync https://www.patreon.com/creatorslug CreatorName
```

---

### Download a Single Video
If you don't want to archive a whole channel, you can download a single transcript:

```bash
./channel-archiver download <VIDEO_URL> [FOLDER_NAME] [--include-comments [N]]
```

---

### Age-Restricted Content & Cookies
Some content requires authentication. The archiver supports on-the-fly cookie extraction from your browser.

1. **Find your browser ID/Profile**:
   ```bash
   ./channel-archiver list-browsers
   ```
2. **Set your preference**:
   ```bash
   echo 'brave:Profile 1' > .browser  # Reads fresh cookies each sync
   ```
3. **Opt-in during sync**:
   ```bash
   ./channel-archiver sync ExampleChannel --use-cookies
   ```

---

### Dry Run / Command Preview
To see exactly what `yt-dlp` commands will be executed without actually performing any downloads:

```bash
./channel-archiver sync <URL> --print-command
```

---

### Configuration & Speaker ID
Each channel folder contains a `config.toml`. You can configure the **Dual Speaker Heuristic** for podcasts:

```toml
url = "https://www.youtube.com/@Example"
uses_dual_speaker_heuristic = true
speaker_a = "ALICE"
speaker_a_strings = ["hello bob", "hi bob"]
speaker_b = "BOB"
speaker_b_strings = ["hello alice", "hi alice"]
```

> [!TIP]
> **How it works**: The heuristic identifies the "Initial Speaker" by finding a greeting string, then toggles speakers every time it sees a `>>` marker in the subtitles.

---

## 📂 Project Structure

Archived data is stored in the `channels/` directory:

```text
channels/
└── <folder_name>/
    ├── data/               # Video folders: YYYYMMDD - Title/
    │   ├── info.json       # Pruned metadata
    │   ├── description.txt
    │   ├── en.srt          # Original subtitles
    │   └── en.txt          # Cleaned transcript
    ├── playlists/          # Playlist metadata (YouTube only)
    ├── archive.txt         # Download history
    ├── config.toml         # URL and speaker heuristics
    ├── PLAYLISTS.md        # Playlist index
    └── TRANSCRIPTS.md      # Chronological video index
```

---

## ⚖️ License

- **Code**: Released under the [Unlicense](LICENSE).
- **Data**: Transcripts and metadata remain the intellectual property of their respective creators.

---
Generated by [warkingtime/channel-transcript-archiver](https://github.com/warkingtime/channel-transcript-archiver).
