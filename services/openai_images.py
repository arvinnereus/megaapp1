"""
services/openai_images.py — Image generation via OpenAI gpt-image-1
=====================================================================
Drop-in replacement for services.kie_ai.generate_image().

Why this exists:
    Kie.ai returns images on a temporary CDN (tempfile.aiquickdraw.com) that
    has had broken TLS for extended outages, leaving generated images
    unreachable. OpenAI's image API returns the bytes directly (base64) so we
    can upload to R2 immediately — no third-party CDN in the loop.

Cost:
    gpt-image-1 medium quality 1024x1536 portrait ~= $0.07 per image
    (compared to ~$0.09 for Kie Nano Banana Pro).
"""

import os
import base64
import time
import re

from openai import OpenAI

from services import r2_storage


def _clean_prompt(prompt):
    """Strip markdown so the image model isn't distracted by formatting tokens."""
    prompt = re.sub(r'\*\*(.+?)\*\*', r'\1', prompt)
    prompt = re.sub(r'__(.+?)__', r'\1', prompt)
    prompt = re.sub(r'\*(.+?)\*', r'\1', prompt)
    prompt = re.sub(r'_(.+?)_', r'\1', prompt)
    prompt = re.sub(r'^#+\s*', '', prompt, flags=re.MULTILINE)
    prompt = re.sub(r'`(.+?)`', r'\1', prompt)
    prompt = prompt.replace('\t', ' ')
    prompt = re.sub(r'\n{3,}', '\n\n', prompt)
    prompt = prompt.replace('"', "'")
    return prompt.strip()


def generate_image(prompt, emit_event=None, reference_image_url=None):
    """
    Generate an image using OpenAI gpt-image-1 and upload straight to R2.

    Signature matches services.kie_ai.generate_image() so the pipeline can swap
    providers with only an import change.
    """
    emit = emit_event or (lambda *a, **kw: None)
    prompt = _clean_prompt(prompt)
    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        emit("image", "progress",
             "No OPENAI_API_KEY set — showing a placeholder. Add your key in Settings to generate real AI images.")
        return {
            "image_url": "https://placehold.co/1080x1920/17181C/C7A35A?text=Add+OpenAI+Key+in+Settings",
            "task_id": "demo_task",
            "duration": 0,
            "cost": 0.0,
            "demo": True,
        }

    if reference_image_url:
        emit("image", "progress",
             "Heads-up: reference-image / headshot consistency is not wired up on the OpenAI provider yet — generating without it.")

    emit("image", "progress",
         "Sending the image description to OpenAI (gpt-image-1, 1024×1536 portrait). Bytes come back directly — no third-party CDN.")

    client = OpenAI(api_key=api_key)
    start = time.time()

    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1536",  # 9:16 portrait, matches the previous Kie aspect ratio
            quality="medium",
            n=1,
        )
    except Exception as e:
        emit("image", "error", f"OpenAI image generation failed: {type(e).__name__}: {e}")
        raise

    duration = round(time.time() - start, 1)

    image_b64 = response.data[0].b64_json
    image_bytes = base64.b64decode(image_b64)

    emit("image", "progress",
         f"OpenAI returned the image ({len(image_bytes):,} bytes) in {duration}s. Saving to your R2 bucket…")

    if r2_storage.is_configured():
        upload_result = r2_storage.upload_bytes(
            image_bytes,
            content_type="image/png",
            folder="images",
            emit_event=emit_event,
        )
        image_url = upload_result["url"]
        task_id = upload_result["key"]
        emit("image", "progress", f"Image safely stored on R2: {image_url}")
    else:
        emit("image", "warning",
             "R2 isn't configured — returning a data URL so the image still shows. Add R2 credentials for permanent hosting.")
        image_url = f"data:image/png;base64,{image_b64}"
        task_id = f"openai_{int(time.time())}"

    return {
        "image_url": image_url,
        "task_id": task_id,
        "duration": duration,
        "cost": 0.07,
        "demo": False,
    }
