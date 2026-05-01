import shutil
import subprocess
import sys
import logging
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)

def check_environment() -> Tuple[bool, Dict[str, bool], List[str]]:
    """
    Checks if the environment is properly set up for yt-dlp and the archiver.
    Returns (overall_success, results_map, missing_critical_items)
    """
    results = {}
    critical_missing = []

    # 1. Check for yt-dlp
    yt_dlp_path = shutil.which("yt-dlp")
    results["yt-dlp"] = yt_dlp_path is not None
    if not results["yt-dlp"]:
        critical_missing.append("yt-dlp")

    # 2. Check for JS Runtime (Deno or Node)
    deno_path = shutil.which("deno")
    node_path = shutil.which("node")
    results["js_runtime"] = (deno_path is not None) or (node_path is not None)
    if not results["js_runtime"]:
        # Technically not critical for all videos, but critical for YouTube challenges
        critical_missing.append("JavaScript Runtime (deno or node)")

    # 3. Check for ffmpeg/ffprobe
    results["ffmpeg"] = shutil.which("ffmpeg") is not None
    results["ffprobe"] = shutil.which("ffprobe") is not None
    if not results["ffmpeg"]:
        critical_missing.append("ffmpeg")

    # 4. Check for curl-cffi (python package)
    try:
        import curl_cffi
        # check if yt-dlp actually supports this version
        try:
            from yt_dlp.dependencies import curl_cffi as ytdl_curl_cffi
            results["curl-cffi"] = ytdl_curl_cffi is not None
        except ImportError:
            results["curl-cffi"] = False
    except ImportError:
        results["curl-cffi"] = False
    
    if not results["curl-cffi"]:
        # Not critical for operation but affects impersonation
        pass

    overall_success = len(critical_missing) == 0
    return overall_success, results, critical_missing

def run_precheck() -> bool:
    """Prints environment status to console. Returns True if OK."""
    success, results, critical = check_environment()
    
    print("\n🔍 Environment Pre-check:")
    
    # Check yt-dlp version
    ytdlp_version = "Unknown"
    if results["yt-dlp"]:
        try:
            ytdlp_version = subprocess.check_output(["yt-dlp", "--version"], text=True).strip()
        except Exception:
            pass
            
    print(f"  - yt-dlp:       {'✅ Found' if results['yt-dlp'] else '❌ Missing'} ({ytdlp_version})")
    print(f"  - JS Runtime:   {'✅ Found (deno/node)' if results['js_runtime'] else '❌ Missing (needed for YouTube challenges)'}")
    print(f"  - ffmpeg:       {'✅ Found' if results['ffmpeg'] else '❌ Missing'}")
    print(f"  - ffprobe:      {'✅ Found' if results['ffprobe'] else '❌ Missing'}")
    print(f"  - curl-cffi:    {'✅ Working' if results['curl-cffi'] else '⚠️  Missing/Unsupported (impersonation disabled)'}")
    
    if not success:
        print("\n❌ CRITICAL DEPENDENCIES MISSING:")
        for item in critical:
            print(f"  - {item}")
        print("\nPlease install missing dependencies to ensure robust archival.")
        return False
    
    print("\n✅ Environment looks good!")
    
    print("\n💡 TIP: If you previously synced a channel with missing dependencies (e.g. no JS runtime),")
    print("        some metadata or formats might be missing. You can re-run the sync with the '--force' flag")
    print("        to ensure everything is correctly archived with the new environment.")
    print("        Example: uv run channel-archiver sync <URL> <NAME> --force")
    
    return True
