import argparse
import sys

from .browser import list_browsers
from .compress import compress_channel
from .extract import download_video, sync_channel
from .extract_cookies import extract_cookies
from .reclean import reclean


def main() -> None:
    parser = argparse.ArgumentParser(
        description="📺 YouTube Channel Transcript Archiver - General CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py sync https://www.youtube.com/@ExampleChannel Example
  python main.py reclean Example
  python main.py cookies chrome
  python main.py compress Example --format tar.xz
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Download command (single video)
    download_parser = subparsers.add_parser("download", help="Download and clean a single video transcript")
    download_parser.add_argument("url", help="YouTube Video URL")
    download_parser.add_argument("name", nargs="?", help="Optional folder name (uploader name used if omitted)")
    download_parser.add_argument("--force", action="store_true", help="Force re-cleaning of transcript")
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

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Archive and sync a YouTube channel or Patreon creator")
    sync_parser.add_argument("url", help="Channel or Creator URL")
    sync_parser.add_argument("name", nargs="?", help="Optional folder name for the channel")
    sync_parser.add_argument("--force", action="store_true", help="Force re-cleaning of all transcripts")
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
    reclean_parser = subparsers.add_parser("reclean", help="Local re-cleanup and re-indexing of a channel")
    reclean_parser.add_argument("name", help="Folder name of the channel to re-clean")

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
    compress_parser = subparsers.add_parser("compress", help="Compress a channel extract into an archive")
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

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    try:
        if args.command == "sync":
            sync_channel(
                args.url,
                folder_name=args.name,
                force=args.force,
                cookies_file=args.cookies,
                cookies_browser=args.cookies_from_browser,
                use_cookies=args.use_cookies,
                print_command=args.print_command,
            )
        elif args.command == "download":
            download_video(
                args.url,
                folder_name=args.name,
                force=args.force,
                cookies_file=args.cookies,
                cookies_browser=args.cookies_from_browser,
                use_cookies=args.use_cookies,
                print_command=args.print_command,
            )
        elif args.command == "reclean":
            reclean(args.name)
        elif args.command == "cookies":
            extract_cookies(args.browser)
        elif args.command == "compress":
            compress_channel(args.name, format=args.format, level=args.level, use_bgzip=args.bgzip)
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
