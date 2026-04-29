"""Shared browser/cookie resolution utilities for yt-dlp."""

import configparser
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any

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
    use_cookies: bool = False,
) -> list[str]:
    """Build the yt-dlp cookie arguments list.

    Priority:
      1. Explicit --cookies or --cookies-from-browser args (from CLI)
      2. If use_cookies is True:
         a. .browser file (reads fresh cookies from browser at runtime)
         b. cookies.txt file (static export)
      3. No cookies
    """
    if cookies_file:
        log.info("Using cookie file: %s", cookies_file)
        return ["--cookies", cookies_file]

    if cookies_from_browser:
        resolved = resolve_browser(cookies_from_browser)
        log.info("Using cookies from browser: %s", resolved)
        return ["--cookies-from-browser", resolved]

    if not use_cookies:
        return []

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
        log.info("Using static cookies.txt.")
        return ["--cookies", "cookies.txt"]

    return []


def _get_chromium_profiles(browser_dir: Path) -> list[dict[str, str]]:
    """Extract profile information from a Chromium browser directory."""
    local_state_path = browser_dir / "Local State"
    if not local_state_path.exists():
        # Fallback: check for Default/Profile folders manually if Local State is missing
        profiles = []
        if (browser_dir / "Default").exists():
            profiles.append({"folder": "Default", "name": "Default"})
        for p in browser_dir.glob("Profile *"):
            if p.is_dir():
                profiles.append({"folder": p.name, "name": p.name})
        return profiles

    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            profiles = []
            for folder, info in info_cache.items():
                name = info.get("name")
                profiles.append({"folder": folder, "name": name})
            return sorted(profiles, key=lambda x: x["folder"])
    except Exception:
        return []


def list_browsers() -> None:
    """List available browsers and discovered profiles for cookie extraction."""
    print("📺 Available Browser IDs for Cookie Extraction:")

    # Define browser paths for the current platform
    system = platform.system()
    home = Path.home()
    browser_configs: list[dict[str, Any]] = []

    if system == "Darwin":
        browser_configs = [
            {"id": "chrome", "name": "Google Chrome", "path": home / "Library/Application Support/Google/Chrome"},
            {
                "id": "brave",
                "name": "Brave",
                "path": home / "Library/Application Support/BraveSoftware/Brave-Browser",
            },
            {"id": "edge", "name": "Microsoft Edge", "path": home / "Library/Application Support/Microsoft Edge"},
            {"id": "opera", "name": "Opera", "path": home / "Library/Application Support/com.operasoftware.Opera"},
            {"id": "safari", "name": "Safari", "path": None},  # Safari profiles are handled differently
            {"id": "firefox", "name": "Firefox", "path": _firefox_profiles_ini_path()},
        ]
    elif system == "Linux":
        # Simplified Linux paths
        browser_configs = [
            {"id": "chrome", "name": "Google Chrome", "path": home / ".config/google-chrome"},
            {"id": "brave", "name": "Brave", "path": home / ".config/BraveSoftware/Brave-Browser"},
            {"id": "firefox", "name": "Firefox", "path": _firefox_profiles_ini_path()},
        ]

    for config in browser_configs:
        b_id: str = config["id"]
        b_name: str = config["name"]
        b_path: Path | None = config["path"]

        if b_id == "firefox":
            print(f"\n{b_name} (use 'firefox:PROFILE_NAME'):")
            if b_path and b_path.is_file():
                try:
                    config_parser = configparser.ConfigParser()
                    config_parser.read(str(b_path))
                    ff_profiles = []
                    for section in config_parser.sections():
                        p_name = config_parser.get(section, "Name", fallback=None)
                        if p_name:
                            ff_profiles.append(p_name)
                    if ff_profiles:
                        for p in sorted(ff_profiles):
                            print(f"  - {p} (use 'firefox:{p}')")
                    else:
                        print("  - (No named profiles found)")
                except Exception:
                    print("  - (Error reading profiles.ini)")
            else:
                print("  - (Not found or profiles.ini missing)")

        elif b_id == "safari":
            print(f"\n{b_name}:")
            print("  - Default (use 'safari')")

        else:
            print(f"\n{b_name} (use '{b_id}:PROFILE_FOLDER'):")
            if b_path and b_path.is_dir():
                chrome_profiles = _get_chromium_profiles(b_path)
                if chrome_profiles:
                    for cp in chrome_profiles:
                        display_name = f"{cp['folder']}"
                        if cp["name"] and cp["name"] != cp["folder"]:
                            display_name += f" ({cp['name']})"
                        print(f"  - {display_name} (use '{b_id}:{cp['folder']}')")
                else:
                    print(f"  - Default (use '{b_id}')")
            else:
                print(f"  - (Not found at expected path: {b_path})")

    print("\nExamples:")
    print("  ./channel-archiver sync <URL> --cookies-from-browser brave:Default")
    print('  ./channel-archiver sync <URL> --cookies-from-browser "chrome:Profile 1"')
    print("  echo 'firefox:work' > .browser")
