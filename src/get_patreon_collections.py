import argparse
import http.cookiejar
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import requests
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


def load_cookies(cookie_file: str) -> http.cookiejar.MozillaCookieJar:
    cj = http.cookiejar.MozillaCookieJar(cookie_file)
    cj.load(ignore_discard=True, ignore_expires=True)
    return cj


def get_campaign_id(url: str, session: requests.Session) -> str | None:
    """Extract campaign ID from Patreon URL."""
    # Try to fetch the page and find it in the HTML
    try:
        response = session.get(url, timeout=10)
        # Patterns found in Patreon HTML
        match = re.search(r'"campaign":\{"data":\{"id":"(\d+)"', response.text)
        if match:
            return match.group(1)
        match = re.search(r'"campaign_id":(\d+)', response.text)
        if match:
            return match.group(1)
        match = re.search(r'/api/campaigns/(\d+)', response.text)
        if match:
            return match.group(1)
    except Exception as e:
        log.error(f"Error fetching campaign ID: {e}")
    return None


def get_collections(url: str, campaign_id: str, session: requests.Session) -> list[dict[str, str]]:
    """Get collections for a campaign using the API or HTML parsing."""
    collections = []
    seen = set()

    # 1. Try the API first (most reliable if it works)
    try:
        api_url = f"https://www.patreon.com/api/campaigns/{campaign_id}?include=collections&fields[collection]=title,description"
        response = session.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Check included objects
            if "included" in data:
                for item in data["included"]:
                    if item.get("type") == "collection":
                        c_id = item.get("id")
                        if c_id and c_id not in seen:
                            collections.append(
                                {
                                    "id": c_id,
                                    "title": item.get("attributes", {}).get("title") or f"Collection {c_id}",
                                    "description": item.get("attributes", {}).get("description") or "",
                                }
                            )
                            seen.add(c_id)
            
            # Check relationships if not all were in included
            rel_cols = data.get("data", {}).get("relationships", {}).get("collections", {}).get("data", [])
            for rc in rel_cols:
                rc_id = rc.get("id")
                if rc_id and rc_id not in seen:
                    # We don't have the title yet, but we have the ID
                    collections.append({"id": rc_id, "title": f"Collection {rc_id}", "description": ""})
                    seen.add(rc_id)
    except Exception as e:
        log.debug(f"API collection fetch failed: {e}")

    if collections:
        return collections

    # 2. Try HTML parsing as fallback
    collections_url = url.rstrip("/") + "/collections"
    try:
        response = session.get(collections_url, timeout=10)
        # Search for __NEXT_DATA__
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response.text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))

            def find_key(obj: Any, key: str) -> Any:
                if isinstance(obj, dict):
                    if key in obj:
                        return obj[key]
                    for v in obj.values():
                        res = find_key(v, key)
                        if res:
                            return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = find_key(item, key)
                        if res:
                            return res
                return None

            bootstrap = find_key(data, "bootstrap")
            if bootstrap and "included" in bootstrap:
                for item in bootstrap["included"]:
                    if item.get("type") == "collection":
                        c_id = item.get("id")
                        if c_id and c_id not in seen:
                            collections.append(
                                {
                                    "id": c_id,
                                    "title": item.get("attributes", {}).get("title"),
                                    "description": item.get("attributes", {}).get("description"),
                                }
                            )
                            seen.add(c_id)
            if collections:
                return collections

        # Fallback: parse links
        matches = re.findall(r'/collections/(\d+)', response.text)
        for c_id in matches:
            if c_id not in seen:
                collections.append({"id": c_id, "title": f"Collection {c_id}", "description": ""})
                seen.add(c_id)
    except Exception as e:
        log.error(f"Error fetching collections from HTML: {e}")
    
    if not collections:
        log.debug("No collections found in HTML. Response snippet: %s", response.text[:500] if 'response' in locals() else "N/A")
    return collections


def fetch_posts_for_collection(campaign_id: str, collection_id: str, session: requests.Session) -> list[dict[str, Any]]:
    """Fetch all posts for a given collection ID."""
    posts = []
    cursor = None
    while True:
        url = f"https://www.patreon.com/api/posts?filter[campaign_id]={campaign_id}&filter[collection_id]={collection_id}&page[size]=100"
        if cursor:
            url += f"&page[cursor]={cursor}"

        response = session.get(url, timeout=10)
        if response.status_code != 200:
            log.error(f"Error fetching posts for collection {collection_id}: {response.status_code}")
            break

        data = response.json()
        for post in data.get("data", []):
            attr = post.get("attributes", {})
            # Convert created_at to YYYYMMDD
            created_at = attr.get("created_at", "")
            upload_date = created_at.split("T")[0].replace("-", "") if created_at else "Unknown"

            posts.append(
                {
                    "id": post.get("id"),
                    "title": attr.get("title"),
                    "webpage_url": f"https://www.patreon.com/posts/{post.get('id')}",
                    "upload_date": upload_date,
                    "description": attr.get("content"),
                }
            )

        # Check for next page
        links = data.get("links", {})
        if "next" in links and links["next"]:
            # Extract cursor from URL
            match = re.search(r"page\[cursor\]=([^&]+)", links["next"])
            if match:
                cursor = match.group(1)
            else:
                break
        else:
            break
    return posts


def download_patreon_collections(
    url: str, channel_dir: str | Path, cookies_path: str = "cookies.txt", collection_ids: str | None = None
) -> None:
    """Main entry point to download Patreon collections as playlist metadata."""
    session = requests.Session()
    if os.path.exists(cookies_path):
        session.cookies = load_cookies(cookies_path)
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        }
    )

    log.info(f"Finding campaign ID for {url}...")
    campaign_id = get_campaign_id(url, session)
    if not campaign_id:
        log.error("Could not find campaign ID. Ensure cookies are valid and URL is correct.")
        return
    log.info(f"Campaign ID: {campaign_id}")

    log.info("Fetching collections...")
    if collection_ids:
        collections = [{"id": i.strip(), "title": f"Collection {i.strip()}"} for i in collection_ids.split(",")]
    else:
        collections = get_collections(url, campaign_id, session)

    if not collections:
        log.info("No collections found.")
        return

    log.info(f"Found {len(collections)} collections.")
    playlists_dir = Path(channel_dir) / "playlists"
    playlists_dir.mkdir(parents=True, exist_ok=True)

    for col in collections:
        title = col["title"]
        c_id = col["id"]
        log.info(f"Fetching posts for collection: {title} ({c_id})...")
        posts = fetch_posts_for_collection(campaign_id, c_id, session)
        log.info(f"  Found {len(posts)} posts.")

        # Create yt-dlp style info.json
        safe_title = "".join(c for c in title if c.isalnum() or c in (" ", ".", "_")).strip()
        playlist_data = {
            "id": c_id,
            "title": title,
            "webpage_url": f"{url.rstrip('/')}/collections/{c_id}",
            "playlist_count": len(posts),
            "entries": posts,
            "extractor": "patreon:collection",
        }

        output_path = playlists_dir / f"{safe_title}.info.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(playlist_data, f, indent=4, ensure_ascii=False)
        log.info(f"  Saved to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Patreon Collections metadata")
    parser.add_argument("url", help="Patreon channel URL")
    parser.add_argument("channel_dir", help="Directory for the channel")
    parser.add_argument("--cookies", default="cookies.txt", help="Path to cookies.txt")
    parser.add_argument("--ids", help="Comma-separated list of collection IDs")

    args = parser.parse_args()
    download_patreon_collections(args.url, args.channel_dir, args.cookies, args.ids)


if __name__ == "__main__":
    main()
