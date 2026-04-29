import argparse
import logging
import subprocess
import sys
from pathlib import Path

from .browser import resolve_browser

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def extract_cookies(browser_name: str) -> None:
    resolved = resolve_browser(browser_name)
    log.info(f"Extracting cookies from {resolved} to cookies.txt...")

    # Remove stale cookies file first
    cookies_file = Path("cookies.txt")
    if cookies_file.is_file():
        cookies_file.unlink()

    # Export fresh cookies — use a real video URL to ensure YouTube auth is exercised
    cmd = [
        "yt-dlp",
        "--cookies-from-browser",
        resolved,
        "--cookies",
        "cookies.txt",
        "--skip-download",
        "--ignore-errors",
        "--no-warnings",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ]

    try:
        subprocess.run(cmd, check=False, capture_output=True)
    except FileNotFoundError:
        log.error("yt-dlp not found. Please install it.")
        sys.exit(1)

    if cookies_file.is_file() and cookies_file.stat().st_size > 0:
        log.info("✅ Success! Cookies extracted to cookies.txt")
        print("\nTIP: YouTube rotates cookies quickly. For best results, save your")
        print("browser preference and use --cookies-from-browser at sync time:")
        print(f"  echo '{browser_name}' > .browser")
        print("\nThen the archiver will read fresh cookies directly from your browser each run.")
    else:
        log.error(f"❌ Failed to extract cookies. Ensure {browser_name} is installed and you are logged into YouTube.")
        if sys.platform == "darwin":
            log.info("On macOS, you might need to grant Full Disk Access to your terminal.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract cookies from your browser to cookies.txt")
    parser.add_argument(
        "browser",
        nargs="?",
        help="Browser name (chrome, firefox, safari, etc.). For Firefox profiles, use 'firefox:profile_name'.",
    )
    args = parser.parse_args()

    if not args.browser:
        parser.print_help()
        print("\nCommon browsers: chrome, firefox, safari, edge, opera, brave, vivaldi")
        print("\nExamples:")
        print("  channel-cookies chrome")
        print("  channel-cookies firefox:alt")
        sys.exit(1)

    extract_cookies(args.browser)


if __name__ == "__main__":
    main()
