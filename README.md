# 📺 YouTube Channel Transcript Archiver

A robust, generalized tool designed to archive metadata, descriptions, and intelligently cleaned transcripts from any YouTube channel. This project automates the pipeline from discovery to high-quality text extraction.  This downloads already made subtitles, it does not use TTS models to generate transcripts.

---

## ✨ Features

- **🚀 Incremental Sync**: Efficiently tracks previously downloaded videos using `archive.txt` to only fetch new content.
- **🧹 Smart Cleaning**: Converts messy SRT subtitles into readable text documents with pause detection (>3s).
- **🗣️ Speaker Identification**: Uses configurable state-machine heuristics (relying on `>>` markers) to identify speakers.
- **🗜️ Metadata Pruning**: Automatically strips large binary fields and PII from `.info.json` files to save space and ensure privacy.
- **📚 Auto-Indexing**: Generates chronological `TRANSCRIPTS.md` and `PLAYLISTS.md` indices for easy navigation.
- **🔄 Local Re-processing**: Ability to re-clean and re-index existing data without re-downloading from YouTube.

---

## 🛠️ Installation

### Prerequisites

Ensure you have the following installed:
- **Python 3.10+**
- **[uv](https://github.com/astral-sh/uv)** (High-performance Python package manager)
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
- **Bash**

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd channel-transcript-archiver
   ```

2. Install dependencies and setup environment:
   ```bash
   uv sync
   ```

---

## 🚀 Usage

### Unified CLI
The easiest way to use the archiver is through the `./channel-archiver` wrapper (which automatically uses `uv`):

```bash
./channel-archiver <command> [args]
```

**Commands:**
- `sync`: Archive and sync a channel.
- `reclean`: Local re-cleanup of a channel.
- `cookies`: Extract cookies from your browser.
- `compress`: Archive a channel directory into a compressed file.

### Archive or Update a Channel
To start archiving a new channel or update an existing one:

```bash
# New channel (requires URL)
./channel-archiver sync <CHANNEL_URL> [FOLDER_NAME] [--use-cookies] [--force]

# Existing channel (can use folder name)
./channel-archiver sync <FOLDER_NAME> [--use-cookies] [--force]
```

**Example:**
```bash
./channel-archiver sync https://www.youtube.com/@ExampleChannel ExampleChannel --use-cookies
# Later, to update:
./channel-archiver sync ExampleChannel
```

### Age-Restricted Content & Cookies
Some videos may be age-restricted and require authentication to download transcripts.

**Recommended: Save your browser preference** (reads fresh cookies each sync):
```bash
echo 'firefox:alt' > .browser      # Or: chrome, safari, firefox:profile_name
```

**Opt-in to cookie usage**:
To prevent accidental data leakage or browser database locking, the archiver only reads from `.browser` or `cookies.txt` if you explicitly pass the `--use-cookies` flag:
```bash
./channel-archiver sync <URL> --use-cookies
```

**Alternative: Export cookies to a file** (may go stale quickly):
```bash
./channel-archiver cookies firefox:alt    # Or: chrome, safari, etc.
```

### Configuration & Speaker ID
When you first sync a channel, a default `config.toml` is created in the channel folder. You can edit this to enable the **Dual Speaker Heuristic**:

```toml
uses_dual_speaker_heuristic = true
speaker_a = "ALICE"
speaker_a_strings = ["hello bob", "hi bob"]
speaker_b = "BOB"
speaker_b_strings = ["hello alice", "hi alice"]
```

> [!IMPORTANT]
> **How it works**: This is a text-based state machine. It identifies the "Initial Speaker" by finding the first occurrence of one of your configured strings. From then on, it **toggles** between the two speakers every time it encounters a `>>` marker in the subtitles.  Thus this heuristic only really works well with two speaker podcast type videos.
>
> **Compatibility**: This heuristic *only* works on transcripts that include `>>` speaker change indicators. YouTube only started adding these to auto-captions relatively recently; older videos will likely lack these markers and thus will not support automated speaker switching.

### Local Re-cleanup
If you've updated your `config.toml` or the cleaning logic, you can re-process existing data without re-downloading:

```bash
./channel-archiver reclean <FOLDER_NAME>
```

### Channel Compression
To archive a channel directory into a single compressed file:

```bash
./channel-archiver compress <FOLDER_NAME> [--format zip|tar.gz|tar.xz] [--level 1-9] [--bgzip]
```

**Options:**
- `--format`: `zip` (default), `tar.gz`, or `tar.xz`.
- `--level`: Compression level from `1` (fastest) to `9` (smallest). Default is `6`.
- `--bgzip`: Uses `bgzip` (Blocked GNU Zip) to create a `.tar.gz` archive that supports random access and parallel decompression. (Requires `bgzip` to be installed).

**Example:**
```bash
./channel-archiver compress ExampleChannel --format tar.xz --level 9
```

---

## 📂 Project Structure

All archived data is stored in the `channels/` directory (ignored by Git):

```text
channels/
└── <channel-handle>/
    ├── data/               # Subdirectories per video: YYYYMMDD - Title/
    │   ├── video.info.json # Pruned metadata
    │   ├── video.description.txt
    │   ├── video.en.srt    # Original subtitles
    │   └── video.en.txt    # Cleaned, speaker-tagged transcript
    ├── playlists/          # Metadata for all channel playlists
    ├── archive.txt         # yt-dlp download history
    ├── config.toml         # Channel-specific speaker heuristics
    ├── PLAYLISTS.md        # Generated index of all playlists
    └── TRANSCRIPTS.md      # Generated chronological list of videos
```

---

## ⚖️ License

- **Code**: This tool is released under the [Unlicense](LICENSE).
- **Data**: All transcripts, metadata, and descriptions archived in the `channels/` directory remain the intellectual property and copyright of their respective YouTube channels.

---

> [!NOTE]
> This project is designed for researchers and archivists. Please respect YouTube's Terms of Service and the creators' content.

