"""
services/getlate.py — Publishing via GetLate.dev
==================================================
Multi-platform social media publishing in one API call.
Students learn: this is the "output" stage — where content goes live.
"""

import os
import requests
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------
GETLATE_BASE_URL = "https://getlate.dev/api/v1"


def _parse_scheduled_time(scheduled_at_str):
    """Parse a scheduled_at string into UTC ISO 8601 format."""
    formats = [
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(scheduled_at_str, fmt)
            dt_utc = dt.replace(tzinfo=timezone.utc)
            return dt_utc.isoformat()
        except (ValueError, TypeError):
            continue
    # Can't parse — return as-is
    return scheduled_at_str


def _get_headers():
    """Build auth headers for GetLate API."""
    api_key = os.getenv("GETLATE_API_KEY")
    if not api_key:
        return None
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


# ---------------------------------------------------------------------------
# publish_post() — Send content to connected social accounts
# ---------------------------------------------------------------------------
def publish_post(content_item, platforms=None, emit_event=None):
    """
    Publish a content item to social media via GetLate.dev.

    Args:
        content_item: dict from the database (must have script, image_url, etc.)
        platforms: list of platform names to publish to (defaults to item's platform)
        emit_event: Callback for SSE logging

    Returns:
        dict with: post_id, platforms_published, status
    """
    emit = emit_event or (lambda *a, **kw: None)
    headers = _get_headers()

    if not platforms:
        platforms = [content_item.get("platform", "instagram")]

    if not headers:
        emit("publish", "progress", "No GetLate API key set yet — simulating publish. To publish for real, get your key from https://getlate.dev and paste it in Settings > GetLate > API Key.")
        return {
            "post_id": "demo_post_id",
            "platforms_published": platforms,
            "status": "demo",
            "demo": True,
            "message": "Get your key from https://getlate.dev and add it in Settings."
        }

    emit("publish", "progress", f"Publishing to {', '.join(platforms)} via GetLate.dev...")

    try:
        # Build the post payload
        payload = {
            "content": content_item.get("script", ""),
            "platforms": [{"platform": p} for p in platforms],
        }

        # Attach image if available (prefer R2 URL)
        image_url = content_item.get("r2_image_url") or content_item.get("image_url")
        if image_url:
            payload["media"] = [{"url": image_url, "type": "image"}]

        # Attach video if available (prefer R2 URL)
        video_url = content_item.get("r2_video_url") or content_item.get("video_url")
        if video_url:
            payload["media"] = payload.get("media", [])
            payload["media"].append({"url": video_url, "type": "video"})

        # If there's a scheduled time, parse and add it
        if content_item.get("scheduled_at"):
            parsed_time = _parse_scheduled_time(content_item["scheduled_at"])
            if parsed_time:
                payload["scheduled_for"] = parsed_time
                payload["timezone"] = "America/Los_Angeles"

        response = requests.post(
            f"{GETLATE_BASE_URL}/posts",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        post_id = data.get("id", data.get("post_id", "unknown"))

        emit("publish", "progress",
             f"Published! Post ID: {post_id}")

        return {
            "post_id": post_id,
            "platforms_published": platforms,
            "status": "published",
            "demo": False,
            "response": data
        }

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        emit("publish", "error", f"GetLate error: {error_msg}")
        raise


# ---------------------------------------------------------------------------
# get_connected_accounts() — List connected social accounts
# ---------------------------------------------------------------------------
def get_connected_accounts(emit_event=None):
    """
    Fetch the list of connected social media accounts from GetLate.dev.

    Returns:
        list of account dicts with: id, platform, username, status
    """
    emit = emit_event or (lambda *a, **kw: None)
    headers = _get_headers()

    if not headers:
        # Return demo accounts so the UI has something to show
        return [
            {"id": "demo_1", "platform": "instagram", "username": "@demo_user", "status": "demo"},
            {"id": "demo_2", "platform": "tiktok", "username": "@demo_user", "status": "demo"},
            {"id": "demo_3", "platform": "linkedin", "username": "Demo User", "status": "demo"},
        ]

    try:
        response = requests.get(
            f"{GETLATE_BASE_URL}/accounts",
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        return response.json().get("accounts", [])

    except requests.exceptions.RequestException as e:
        emit("publish", "error", f"Failed to fetch connected accounts: {str(e)}")
        return []
