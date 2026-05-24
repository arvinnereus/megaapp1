"""
services/openrouter.py — LLM Integration via OpenRouter
=========================================================
Uses the openai Python library with a base_url swap to hit OpenRouter.
This means any model on OpenRouter works with the same code pattern.

Model: google/gemini-2.5-flash (fast + cheap — great for teaching demos)
"""

import os
import json
from openai import OpenAI

# ---------------------------------------------------------------------------
# Platform-specific character limits
# Students learn: each platform has different constraints
# ---------------------------------------------------------------------------
PLATFORM_LIMITS = {
    "twitter":   280,
    "linkedin":  3000,
    "instagram": 2200,
    "tiktok":    4000,
    "youtube":   5000,
    "facebook":  63206,
}

# Default model — fast and cheap for teaching
DEFAULT_MODEL = "google/gemini-2.5-flash"


def _get_client():
    """
    Create an OpenAI client pointed at OpenRouter.
    Falls back to a demo mode if no API key is set.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": os.getenv("APP_URL", "http://localhost:5000"),
            "X-Title": "Content Automation Demo"
        }
    )


def _demo_response(description):
    """Return a mock response when no API key is configured."""
    return {
        "text": (
            f"Hey! You're running in demo mode right now.\n\n"
            f"To get real AI-generated content, grab a free API key from OpenRouter:\n"
            f"1. Go to https://openrouter.ai/keys\n"
            f"2. Create an account and copy your key\n"
            f"3. Paste it in Settings > OpenRouter > API Key\n\n"
            f"Once you do that, this will generate real scripts, captions, and image prompts!"
        ),
        "model": "demo",
        "tokens_in": 0,
        "tokens_out": 0,
        "cost": 0.0,
        "demo": True
    }


# ---------------------------------------------------------------------------
# generate_script() — Turn an article/idea into a social media post
# ---------------------------------------------------------------------------
def generate_script(article_text_or_idea, platform="instagram", input_type="idea", emit_event=None):
    """
    Generate a social media post script from an article or idea.

    Args:
        article_text_or_idea: The scraped article text or raw idea string
        platform: Target platform (instagram, tiktok, linkedin, etc.)
        input_type: 'url' (article was scraped) or 'idea' (raw input)
        emit_event: Optional callback for SSE logging

    Returns:
        dict with: text, model, tokens_in, tokens_out, cost
    """
    emit = emit_event or (lambda *a, **kw: None)
    client = _get_client()

    if not client:
        emit("script", "progress", "No OpenRouter API key set yet — using demo content so you can see how the pipeline flows. Add your key in Settings to use real AI!")
        return _demo_response("Script generation requires an OpenRouter API key")

    char_limit = PLATFORM_LIMITS.get(platform, 2200)

    # Build the system prompt — educational tone, content-creator focused
    system_prompt = f"""You are an expert social media content creator. Your job is to create
engaging, scroll-stopping posts for {platform}.

RULES:
- Maximum {char_limit} characters
- Write in a conversational, authentic tone
- Include a strong hook in the first line
- End with a clear call-to-action
- Use relevant emojis sparingly (2-4 max)
- Include 3-5 relevant hashtags at the end
- Format for {platform} (line breaks, spacing)

OUTPUT FORMAT: Return ONLY the post text. No explanations, no preamble."""

    # Build the user prompt based on input type
    if input_type == "url":
        user_prompt = f"""Transform this article into a {platform} post:

---
{article_text_or_idea[:4000]}
---

Create a compelling post that captures the key insight from this article."""
    else:
        user_prompt = f"""Create a {platform} post about this topic/idea:

{article_text_or_idea}

Make it engaging, informative, and ready to publish."""

    emit("script", "progress", f"Calling OpenRouter → using the {DEFAULT_MODEL} model. OpenRouter is like a phone operator — it connects us to whichever AI model we pick.")

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.8,
        )

        # Extract the response
        text = response.choices[0].message.content.strip()
        usage = response.usage

        result = {
            "text": text,
            "model": DEFAULT_MODEL,
            "tokens_in": usage.prompt_tokens if usage else 0,
            "tokens_out": usage.completion_tokens if usage else 0,
            "cost": _estimate_cost(usage.prompt_tokens, usage.completion_tokens) if usage else 0.0,
            "demo": False
        }

        emit("script", "progress",
             f"AI wrote back! {result['tokens_out']} tokens (think of tokens like word-pieces). This call cost ${result['cost']:.4f} — pennies per post.")

        return result

    except Exception as e:
        emit("script", "error", f"OpenRouter error: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# generate_image_prompt() — Create an image prompt from the script
# ---------------------------------------------------------------------------
def generate_image_prompt(script_text, emit_event=None):
    """
    Generate a descriptive image prompt from a social media script.
    This prompt will be sent to Kie.ai for image generation.

    Returns:
        dict with: text (the image prompt), model, tokens_in, tokens_out, cost
    """
    emit = emit_event or (lambda *a, **kw: None)
    client = _get_client()

    if not client:
        emit("image", "progress", "No OpenRouter API key — using a demo image prompt. Add your key in Settings to get AI-generated image descriptions!")
        return _demo_response("Image prompt generation requires an OpenRouter API key")

    system_prompt = """You are an expert at creating AI image generation prompts.
Given a social media post, create a single vivid image prompt that would make
a perfect visual companion for the post.

RULES:
- Describe the scene in detail (lighting, mood, colors, composition)
- Use photographic/artistic style keywords
- Keep it under 200 words
- Make it visually striking and scroll-stopping
- Do NOT include any text or words in the image description
- Describe a SCENE, not text overlays

OUTPUT FORMAT: Return ONLY the image prompt. No explanations."""

    emit("image", "progress", "Asking AI to describe a picture that matches your post — this description is called a 'prompt' and it tells the image AI exactly what to draw.")

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create an image prompt for this post:\n\n{script_text}"}
            ],
            max_tokens=300,
            temperature=0.9,
        )

        text = response.choices[0].message.content.strip()
        usage = response.usage

        result = {
            "text": text,
            "model": DEFAULT_MODEL,
            "tokens_in": usage.prompt_tokens if usage else 0,
            "tokens_out": usage.completion_tokens if usage else 0,
            "cost": _estimate_cost(usage.prompt_tokens, usage.completion_tokens) if usage else 0.0,
            "demo": False
        }

        emit("image", "progress", f"Image description is ready ({result['tokens_out']} tokens). Now sending it to Kie.ai to actually create the picture...")
        return result

    except Exception as e:
        emit("image", "error", f"OpenRouter error: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# generate_captions() — Platform-specific captions
# ---------------------------------------------------------------------------
def generate_captions(script_text, platforms=None, emit_event=None):
    """
    Generate platform-specific captions from a script.
    Returns a dict keyed by platform name.

    Returns:
        dict with: captions (dict of platform->caption), model, tokens_in, tokens_out, cost
    """
    emit = emit_event or (lambda *a, **kw: None)
    client = _get_client()

    if not platforms:
        platforms = ["instagram", "tiktok", "linkedin"]

    if not client:
        emit("caption", "progress", "No OpenRouter API key — using demo captions. Add your key in Settings to get real AI-written captions for each platform!")
        demo_captions = {p: f"[DEMO] Caption for {p}" for p in platforms}
        return {
            "captions": demo_captions,
            "model": "demo",
            "tokens_in": 0,
            "tokens_out": 0,
            "cost": 0.0,
            "demo": True
        }

    # Build platform instructions
    platform_instructions = "\n".join([
        f"- {p.upper()}: max {PLATFORM_LIMITS.get(p, 2200)} chars, tailored to {p}'s audience"
        for p in platforms
    ])

    system_prompt = f"""You are a social media expert who adapts content for different platforms.
Given a post script, create tailored captions for each platform.

PLATFORMS TO GENERATE:
{platform_instructions}

OUTPUT FORMAT: Return valid JSON with platform names as keys and captions as values.
Example: {{"instagram": "caption here...", "tiktok": "caption here..."}}
Return ONLY the JSON. No markdown code blocks, no explanations."""

    emit("caption", "progress", f"Asking AI to write custom captions for {', '.join(platforms)}. Each platform gets its own version — different length, hashtags, and style.")

    try:
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Adapt this script for each platform:\n\n{script_text}"}
            ],
            max_tokens=2000,
            temperature=0.7,
        )

        raw_text = response.choices[0].message.content.strip()
        usage = response.usage

        # Parse the JSON response
        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]  # Remove first line
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        try:
            captions = json.loads(raw_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, create a simple dict with the raw text
            captions = {p: raw_text for p in platforms}

        result = {
            "captions": captions,
            "model": DEFAULT_MODEL,
            "tokens_in": usage.prompt_tokens if usage else 0,
            "tokens_out": usage.completion_tokens if usage else 0,
            "cost": _estimate_cost(usage.prompt_tokens, usage.completion_tokens) if usage else 0.0,
            "demo": False
        }

        emit("caption", "progress",
             f"Got captions for {len(captions)} platforms! Cost: ${result['cost']:.4f}. Notice how one AI call can output multiple results — that's efficiency!")

        return result

    except Exception as e:
        emit("caption", "error", f"OpenRouter error: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# Cost estimation helper
# Gemini 2.5 Flash pricing (approximate via OpenRouter)
# ---------------------------------------------------------------------------
def _estimate_cost(tokens_in, tokens_out):
    """
    Estimate the cost of an OpenRouter API call.
    Gemini 2.5 Flash: ~$0.15/M input, ~$0.60/M output (via OpenRouter)
    """
    cost_in = (tokens_in / 1_000_000) * 0.15
    cost_out = (tokens_out / 1_000_000) * 0.60
    return round(cost_in + cost_out, 6)
