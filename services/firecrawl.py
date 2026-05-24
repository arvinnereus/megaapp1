"""
services/firecrawl.py — URL Scraping via FireCrawl
====================================================
Takes a URL, returns clean markdown text of the article.
Students learn: this is the "input" stage — garbage in, garbage out.
"""

import os

# ---------------------------------------------------------------------------
# scrape_url() — Fetch a URL and return clean markdown
# ---------------------------------------------------------------------------
def scrape_url(url, emit_event=None):
    """
    Scrape a URL using the FireCrawl API and return structured content.

    Args:
        url: The URL to scrape
        emit_event: Optional callback for SSE logging

    Returns:
        dict with: markdown, title, word_count

    Raises:
        Exception on scraping failure
    """
    emit = emit_event or (lambda *a, **kw: None)

    api_key = os.getenv("FIRECRAWL_API_KEY")

    if not api_key:
        emit("scrape", "progress", "No FireCrawl API key — using demo content. Add your key in Settings to scrape real articles from the web!")
        return {
            "markdown": (
                f"# Demo Article\n\n"
                f"This is demo content because no FIRECRAWL_API_KEY is set.\n\n"
                f"**Original URL:** {url}\n\n"
                f"In production, FireCrawl would fetch the article at this URL, "
                f"strip out ads, navigation, and boilerplate, and return clean "
                f"markdown text that we can feed into the LLM.\n\n"
                f"Set your FireCrawl API key in Settings to enable real scraping."
            ),
            "title": "Demo Article (Set FireCrawl API Key)",
            "word_count": 52,
            "demo": True
        }

    emit("scrape", "progress", f"Sending your link to FireCrawl — it visits the page, strips out all the ads and menus, and gives us just the article text.")

    try:
        # Import here so the app doesn't crash if firecrawl-py isn't installed
        from firecrawl import FirecrawlApp

        fc = FirecrawlApp(api_key=api_key)

        emit("scrape", "progress", "FireCrawl is reading the webpage now... (this usually takes 1-3 seconds)")

        # Handle both firecrawl-py v1 (scrape_url) and v4+ (scrape)
        if hasattr(fc, "scrape_url"):
            result = fc.scrape_url(url, params={"formats": ["markdown"]})
        else:
            result = fc.scrape(url, formats=["markdown"])

        # v1 returns dict, v4 returns Document object — handle both
        if isinstance(result, dict):
            markdown = result.get("markdown", "")
            metadata = result.get("metadata", {})
        else:
            markdown = getattr(result, "markdown", "") or ""
            metadata = getattr(result, "metadata", {}) or {}

        if isinstance(metadata, dict):
            title = metadata.get("title", metadata.get("ogTitle", "Untitled Article"))
        else:
            title = getattr(metadata, "title", None) or getattr(metadata, "ogTitle", "Untitled Article")

        # Calculate word count
        word_count = len(markdown.split()) if markdown else 0

        emit("scrape", "progress", f"Got it! Pulled {word_count:,} words from \"{title[:50]}\". Clean text, no junk — ready for AI to rewrite.")

        return {
            "markdown": markdown,
            "title": title,
            "word_count": word_count,
            "demo": False
        }

    except ImportError:
        emit("scrape", "error", "firecrawl-py not installed. Run: pip install firecrawl-py")
        raise Exception("firecrawl-py library not installed")

    except Exception as e:
        error_msg = str(e)

        # Friendly error messages for common issues
        if "401" in error_msg or "Unauthorized" in error_msg:
            emit("scrape", "error", "Invalid FireCrawl API key — check Settings")
        elif "429" in error_msg or "rate" in error_msg.lower():
            emit("scrape", "error", "FireCrawl rate limit hit — wait a moment and retry")
        elif "timeout" in error_msg.lower():
            emit("scrape", "error", "FireCrawl request timed out — the URL may be slow")
        else:
            emit("scrape", "error", f"FireCrawl error: {error_msg}")

        raise
