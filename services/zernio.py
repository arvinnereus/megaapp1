"""Social media publishing via Zernio (formerly GetLate.dev)."""
import os


def publish_post(content_item, platforms=None, emit_event=None):
    """Publish content to social media via Zernio API."""
    api_key = os.getenv("ZERNIO_API_KEY") or os.getenv("GETLATE_API_KEY", "")
    if not api_key:
        return {"status": "demo", "post_id": "demo-123", "platforms": platforms or ["demo"]}

    # Try the official SDK first, fall back to legacy getlate module
    try:
        from zernio import Zernio
        client = Zernio(api_key=api_key)

        # Build platform list from connected accounts
        accounts = client.accounts.list()
        target_platforms = []
        for acct in accounts:
            if platforms is None or acct.get("platform") in platforms:
                target_platforms.append({
                    "platform": acct["platform"],
                    "accountId": acct["_id"],
                })

        if not target_platforms:
            return {"status": "no_accounts", "error": "No connected accounts match requested platforms"}

        # Build media items
        media_items = []
        image_url = content_item.get("r2_image_url") or content_item.get("image_url")
        video_url = content_item.get("r2_video_url") or content_item.get("video_url")
        if video_url:
            media_items.append({"type": "video", "url": video_url})
        elif image_url:
            media_items.append({"type": "image", "url": image_url})

        # Get caption
        caption = content_item.get("script", "")
        captions = content_item.get("captions")
        if isinstance(captions, dict) and target_platforms:
            first_platform = target_platforms[0]["platform"]
            caption = captions.get(first_platform, caption)

        post_kwargs = {
            "content": caption,
            "platforms": target_platforms,
        }
        if media_items:
            post_kwargs["media_items"] = media_items

        result = client.posts.create(**post_kwargs)
        return {"status": "published", "post_id": result.get("_id", ""), "platforms": [p["platform"] for p in target_platforms]}

    except ImportError:
        # Fall back to legacy getlate.py
        try:
            from services.getlate import publish_post as legacy_publish
            return legacy_publish(content_item, platforms, emit_event)
        except ImportError:
            return {"status": "error", "error": "Neither zernio-sdk nor getlate module available"}


def get_connected_accounts():
    """Get list of connected social media accounts."""
    api_key = os.getenv("ZERNIO_API_KEY") or os.getenv("GETLATE_API_KEY", "")
    if not api_key:
        return [
            {"platform": "instagram", "name": "Demo Account", "_id": "demo-ig"},
            {"platform": "tiktok", "name": "Demo Account", "_id": "demo-tt"},
            {"platform": "facebook", "name": "Demo Account", "_id": "demo-fb"},
        ]

    try:
        from zernio import Zernio
        client = Zernio(api_key=api_key)
        return client.accounts.list()
    except ImportError:
        try:
            from services.getlate import get_connected_accounts as legacy_get
            return legacy_get()
        except ImportError:
            return []
