import argparse
import sys

from .browser import list_browsers
from .compress import compress_channel
from .extract import download_video, sync_channel
from .extract_cookies import extract_cookies
from .list_channels import list_channels
from .precheck import run_precheck
from .reclean import reclean


def main() -> None:
    parser = argparse.ArgumentParser(
        description="📺 YouTube Channel Transcript Archiver\n\nAutomated archival of YouTube/Patreon metadata, descriptions, and transcripts.\nEnsures high-quality, speaker-tagged transcripts and organized metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Requirements:
  - yt-dlp (Required)
  - JavaScript Runtime (deno or node) - Required for YouTube challenges
  - ffmpeg/ffprobe - Required for processing
  - curl-cffi (Optional) - Required for impersonation

Examples:
  python channel-archiver sync https://www.youtube.com/@ExampleChannel Example
  python channel-archiver sync-all --force
  python channel-archiver download https://www.youtube.com/watch?v=...
  python channel-archiver reclean Example
  python channel-archiver cookies chrome
  python channel-archiver compress Example --format tar.xz
  python channel-archiver precheck
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Download command (single video)
    download_parser = subparsers.add_parser("download", help="Download and clean a single video transcript")
    download_parser.add_argument("url", help="YouTube Video URL")
    download_parser.add_argument("name", nargs="?", help="Optional folder name (uploader name used if omitted)")
    download_parser.add_argument("--force", action="store_true", help="Force re-downloading of metadata and re-cleaning of transcript")
    download_parser.add_argument("--cookies", help="Path to a cookies.txt file")
    download_parser.add_argument("--cookies-from-browser", help="Browser to extract cookies from")
    download_parser.add_argument(
        "--use-cookies",
        action="store_true",
        help="Enable cookie usage (required to use .browser or cookies.txt)",
    )
    download_parser.add_argument(
        "--print-command",
        action="store_true",
        help="Print the yt-dlp command that would be executed instead of running it",
    )
    download_parser.add_argument(
        "--include-comments",
        type=int,
        default=10,
        help="Include top N comments in metadata (Active by default, default: 10)",
    )
    download_parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Disable comment extraction",
    )

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Archive and sync a YouTube channel or Patreon creator")
    sync_parser.add_argument("url", help="Channel or Creator URL (or folder name of an existing channel)")
    sync_parser.add_argument("name", nargs="?", help="Optional folder name for the channel")
    sync_parser.add_argument("--force", action="store_true", help="Ignore archive.txt and force re-sync/re-clean of all items")
    sync_parser.add_argument("--cookies", help="Path to a cookies.txt file")
    sync_parser.add_argument("--cookies-from-browser", help="Browser to extract cookies from")
    sync_parser.add_argument(
        "--use-cookies",
        action="store_true",
        help="Enable cookie usage (required to use .browser or cookies.txt)",
    )
    sync_parser.add_argument(
        "--print-command",
        action="store_true",
        help="Print the yt-dlp command that would be executed instead of running it",
    )
    sync_parser.add_argument(
        "--include-comments",
        type=int,
        default=10,
        help="Include top N comments in metadata (Active by default, default: 10)",
    )
    sync_parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Disable comment extraction",
    )

    # Sync-all command
    sync_all_parser = subparsers.add_parser("sync-all", help="Sync all currently archived channels in sequence")
    sync_all_parser.add_argument("--force", action="store_true", help="Ignore archive.txt and force re-sync/re-clean for all channels")
    sync_all_parser.add_argument("--cookies", help="Path to a cookies.txt file")
    sync_all_parser.add_argument("--cookies-from-browser", help="Browser to extract cookies from")
    sync_all_parser.add_argument(
        "--use-cookies",
        action="store_true",
        help="Enable cookie usage",
    )
    sync_all_parser.add_argument(
        "--include-comments",
        type=int,
        default=10,
        help="Include top N comments in metadata (Active by default, default: 10)",
    )
    sync_all_parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Disable comment extraction",
    )
    reclean_parser = subparsers.add_parser("reclean", help="Locally re-process transcripts, re-index playlists, and update reports")
    reclean_parser.add_argument("name", help="Folder name of the channel to re-clean")

    # List channels command
    subparsers.add_parser("list-channels", help="List currently synced channels and their metadata")

    # List browsers command
    subparsers.add_parser("list-browsers", help="List available browsers and Firefox profiles for cookies")

    # Cookies command
    cookies_parser = subparsers.add_parser("cookies", help="Extract fresh cookies from a browser to cookies.txt")
    cookies_parser.add_argument(
        "browser",
        help=(
            "Browser name (chrome, firefox, safari, edge, opera, brave, vivaldi). "
            "Use 'firefox:profile' for specific profiles."
        ),
    )

    # Compress command
    compress_parser = subparsers.add_parser("compress", help="Compress a channel directory into an archive (zip/tar)")
    compress_parser.add_argument("name", help="Folder name of the channel to compress")
    compress_parser.add_argument(
        "--format",
        choices=["zip", "tar.gz", "tar.xz"],
        default="zip",
        help="Compression format (default: zip, use tar.xz for highest compression)",
    )
    compress_parser.add_argument(
        "--level", type=int, choices=range(1, 10), default=6, help="Compression level (1-9, default: 6)"
    )
    compress_parser.add_argument(
        "--bgzip",
        action="store_true",
        help="Use bgzip (Blocked GNU Zip) for compression (requires bgzip to be installed)",
    )

    # Precheck command
    subparsers.add_parser("precheck", help="Verify that all dependencies and runtimes are correctly installed")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    try:
        if args.command == "precheck":
            run_precheck()
            return

        if args.command == "sync":
            # Auto-run precheck but don't exit on failure, just warn
            run_precheck()
            num_comments = 0 if args.no_comments else args.include_comments
            sync_channel(
                args.url,
                folder_name=args.name,
                force=args.force,
                cookies_file=args.cookies,
                cookies_browser=args.cookies_from_browser,
                use_cookies=args.use_cookies,
                print_command=args.print_command,
                include_comments=num_comments,
            )
        elif args.command == "sync-all":
            run_precheck()
            from pathlib import Path
            channels_dir = Path("channels")
            if not channels_dir.exists():
                print("No channels found.")
                return
            
            num_comments = 0 if args.no_comments else args.include_comments
            for channel_dir in sorted(channels_dir.iterdir()):
                if channel_dir.is_dir() and not channel_dir.name.startswith("."):
                    print(f"\n🔄 Syncing all: {channel_dir.name}...")
                    sync_channel(
                        str(channel_dir.name),
                        force=args.force,
                        cookies_file=args.cookies,
                        cookies_browser=args.cookies_from_browser,
                        use_cookies=args.use_cookies,
                        include_comments=num_comments,
                    )
        elif args.command == "download":
            run_precheck()
            num_comments = 0 if args.no_comments else args.include_comments
            download_video(
                args.url,
                folder_name=args.name,
                force=args.force,
                cookies_file=args.cookies,
                cookies_browser=args.cookies_from_browser,
                use_cookies=args.use_cookies,
                print_command=args.print_command,
                include_comments=num_comments,
            )
        elif args.command == "reclean":
            reclean(args.name)
        elif args.command == "cookies":
            extract_cookies(args.browser)
        elif args.command == "compress":
            compress_channel(args.name, format=args.format, level=args.level, use_bgzip=args.bgzip)
        elif args.command == "list-channels":
            list_channels()
        elif args.command == "list-browsers":
            list_browsers()
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
