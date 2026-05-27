"""
services/gemini_images.py — Image generation via Google Gemini Nano Banana.

Uses the REST API directly (no extra SDK dependency). Cost ~$0.04/image,
with a free tier of 1,500 requests/day. Output bytes are uploaded straight
to Cloudflare R2 — no third-party CDN in the loop.

Signature matches services.openai_images and services.kie_ai so the
content/avatar dispatchers can route to any provider interchangeably.
"""

import os
import re
import time
import base64

import requests

from services import r2_storage


GEMINI_URL_TMPL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)


def _clean_prompt(prompt):
    prompt = re.sub(r'\*\*(.+?)\*\*', r'\1', prompt)
    prompt = re.sub(r'__(.+?)__', r'\1', prompt)
    prompt = re.sub(r'\*(.+?)\*', r'\1', prompt)
    prompt = re.sub(r'_(.+?)_', r'\1', prompt)
    prompt = re.sub(r'^#+\s*', '', prompt, flags=re.MULTILINE)
    prompt = re.sub(r'`(.+?)`', r'\1', prompt)
    prompt = re.sub(r'\n{3,}', '\n\n', prompt)
    return prompt.strip()


def _demo_result():
    return {
        "image_url": "https://placehold.co/1024x1024/17181C/C7A35A?text=Add+GEMINI_API_KEY",
        "task_id": "demo_task",
        "duration": 0,
        "cost": 0.0,
        "demo": True,
    }


def _call_gemini(prompt, refs, emit_event=None):
    """
    refs: list of (bytes, content_type) tuples (may be empty for text-to-image).
    Returns the standard {image_url, task_id, duration, cost, demo} dict.
    """
    emit = emit_event or (lambda *a, **kw: None)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _demo_result()

    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image").strip()
    prompt = _clean_prompt(prompt)

    parts = [{"text": prompt}]
    for data, ct in refs:
        parts.append({
            "inline_data": {
                "mime_type": ct or "image/jpeg",
                "data": base64.b64encode(data).decode("ascii"),
            }
        })

    emit("image", "progress",
         f"Calling Gemini {model} with {len(refs)} reference image(s)…")

    start = time.time()
    try:
        r = requests.post(
            GEMINI_URL_TMPL.format(model=model, key=api_key),
            json={"contents": [{"parts": parts}]},
            timeout=90,
        )
    except Exception as e:
        emit("image", "error", f"Gemini request failed: {type(e).__name__}: {e}")
        raise

    duration = round(time.time() - start, 1)

    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code}: {r.text[:300]}")

    data = r.json()

    image_bytes = None
    image_mime = "image/png"
    for cand in data.get("candidates", []) or []:
        for part in (cand.get("content") or {}).get("parts", []) or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                image_bytes = base64.b64decode(inline["data"])
                image_mime = (inline.get("mimeType") or inline.get("mime_type")
                              or "image/png")
                break
        if image_bytes:
            break

    if not image_bytes:
        # Surface the prompt-feedback if the model refused (safety filters etc.)
        feedback = data.get("promptFeedback") or data.get("prompt_feedback")
        raise RuntimeError(f"Gemini returned no image. Response: {str(feedback or data)[:300]}")

    emit("image", "progress",
         f"Gemini returned {len(image_bytes):,} bytes in {duration}s. Saving to R2…")

    if r2_storage.is_configured():
        up = r2_storage.upload_bytes(
            image_bytes, content_type=image_mime, folder="images", emit_event=emit_event)
        image_url = up["url"]
        task_id = up["key"]
    else:
        image_url = (f"data:{image_mime};base64,"
                     + base64.b64encode(image_bytes).decode("ascii"))
        task_id = f"gemini_{int(time.time())}"

    return {
        "image_url": image_url,
        "task_id": task_id,
        "duration": duration,
        "cost": 0.04,
        "demo": False,
    }


def generate_image(prompt, emit_event=None, reference_image_url=None):
    """
    Text-to-image (optionally with reference URL(s) — pulled and inlined).
    Same signature as openai_images.generate_image and kie_ai.generate_image.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _demo_result()

    refs_urls = []
    if isinstance(reference_image_url, str) and reference_image_url:
        refs_urls = [reference_image_url]
    elif isinstance(reference_image_url, (list, tuple)):
        refs_urls = [u for u in reference_image_url if u]

    refs = []
    for u in refs_urls:
        rr = requests.get(u, timeout=15)
        rr.raise_for_status()
        refs.append((rr.content, rr.headers.get("Content-Type", "image/jpeg")))

    return _call_gemini(prompt, refs, emit_event=emit_event)


def generate_image_with_references(prompt, references, emit_event=None):
    """
    Same shape as openai_images.generate_image_with_references — accepts raw
    bytes so the avatar blueprint can pass uploaded files directly.

    references: list of (bytes, filename) OR (bytes, filename, content_type) tuples.
    """
    normalized = []
    for ref in references or []:
        if isinstance(ref, tuple):
            if len(ref) == 3:
                data, _name, ct = ref
            elif len(ref) == 2:
                data, _name = ref
                ct = "image/jpeg"
            else:
                continue
        else:
            data, ct = ref, "image/jpeg"
        normalized.append((data, ct))

    return _call_gemini(prompt, normalized, emit_event=emit_event)
