"""Shared browser/cookie resolution utilities for yt-dlp."""

import configparser
import logging
import os
import platform
from pathlib import Path

log = logging.getLogger(__name__)


def _firefox_profiles_ini_path() -> Path | None:
    """Return the path to Firefox's profiles.ini, or None if not found."""
    system = platform.system()
    if system == "Darwin":
        p = Path.home() / "Library" / "Application Support" / "Firefox" / "profiles.ini"
    elif system == "Linux":
        p = Path.home() / ".mozilla" / "firefox" / "profiles.ini"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        p = Path(appdata) / "Mozilla" / "Firefox" / "profiles.ini" if appdata else None  # type: ignore[assignment]
    else:
        return None
    return p if p and p.is_file() else None


def resolve_browser(browser: str) -> str:
    """Resolve a browser string like 'firefox:alt' to a full profile path.

    yt-dlp expects 'firefox:/absolute/path/to/profile' for non-default profiles.
    This function resolves friendly profile names (e.g. 'alt') to absolute paths
    by reading Firefox's profiles.ini.

    For non-Firefox browsers or already-absolute paths, returns the input unchanged.
    """
    if not browser.startswith("firefox:"):
        return browser

    profile_name = browser.split(":", 1)[1]

    # Already an absolute path — don't resolve
    if profile_name.startswith("/"):
        return browser

    profiles_ini = _firefox_profiles_ini_path()
    if profiles_ini is None:
        log.warning("Could not find Firefox profiles.ini")
        return browser

    config = configparser.ConfigParser()
    config.read(str(profiles_ini))

    firefox_dir = profiles_ini.parent

    for section in config.sections():
        if config.get(section, "Name", fallback=None) == profile_name:
            rel_path = config.get(section, "Path", fallback=None)
            is_relative = config.getboolean(section, "IsRelative", fallback=True)
            if rel_path:
                if is_relative:
                    full_path = firefox_dir / rel_path
                else:
                    full_path = Path(rel_path)
                resolved = f"firefox:{full_path}"
                log.info("Resolved Firefox profile '%s' → %s", profile_name, resolved)
                return resolved

    log.warning("Firefox profile '%s' not found in %s", profile_name, profiles_ini)
    return browser


def get_cookie_args(
    *,
    cookies_file: str | None = None,
    cookies_from_browser: str | None = None,
) -> list[str]:
    """Build the yt-dlp cookie arguments list.

    Priority:
      1. Explicit --cookies or --cookies-from-browser args (from CLI)
      2. .browser file (reads fresh cookies from browser at runtime — recommended)
      3. cookies.txt file (static export — may go stale)
      4. No cookies
    """
    if cookies_file:
        log.info("Using cookie file: %s", cookies_file)
        return ["--cookies", cookies_file]

    if cookies_from_browser:
        resolved = resolve_browser(cookies_from_browser)
        log.info("Using cookies from browser: %s", resolved)
        return ["--cookies-from-browser", resolved]

    # Auto-detect from .browser file
    browser_file = Path(".browser")
    if browser_file.is_file():
        browser_name = browser_file.read_text().strip()
        if browser_name:
            resolved = resolve_browser(browser_name)
            log.info("Using cookies from browser (via .browser): %s", browser_name)
            return ["--cookies-from-browser", resolved]

    # Fall back to static cookies.txt
    if Path("cookies.txt").is_file():
        log.warning("Using static cookies.txt (may be stale). Consider: echo 'firefox:alt' > .browser")
        return ["--cookies", "cookies.txt"]

    return []
