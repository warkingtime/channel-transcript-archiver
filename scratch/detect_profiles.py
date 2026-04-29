import json
import os
from pathlib import Path

def get_chromium_profiles(browser_path):
    local_state_path = Path(browser_path) / "Local State"
    if not local_state_path.exists():
        return []
    
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            profiles = []
            for folder, info in info_cache.items():
                name = info.get("name")
                profiles.append({"folder": folder, "name": name})
            return profiles
    except Exception as e:
        print(f"Error: {e}")
        return []

home = os.path.expanduser("~")
browsers = {
    "Chrome": f"{home}/Library/Application Support/Google/Chrome",
    "Brave": f"{home}/Library/Application Support/BraveSoftware/Brave-Browser",
    "Edge": f"{home}/Library/Application Support/Microsoft Edge",
}

for name, path in browsers.items():
    print(f"\n{name}:")
    profiles = get_chromium_profiles(path)
    for p in profiles:
        print(f"  {p['folder']} -> {p['name']}")
