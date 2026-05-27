"""
Avatar generator — upload your photo (+ optional reference), describe the scene,
get a new AI-generated avatar.

Provider strategy:
  - Respects IMAGE_PROVIDER env var ("openai" | "kie").
  - Auto-falls-back to the other provider if the primary fails (e.g. Kie's
    tempfile CDN unreachable, OpenAI rate-limit, etc.).

The final image is always served from your own R2 bucket — no third-party
temp URLs leak through to the browser.
"""
import os

from flask import Blueprint, render_template, request, jsonify

from auth import login_required
from services import r2_storage, openai_images, gemini_images
from services.kie_ai import generate_image as kie_generate_image

avatar_bp = Blueprint("avatar", __name__)


# ---------------------------------------------------------------------------
# Default system-style instructions wrapped around the user's prompt.
# Goal: identity preservation + photo-realistic environmental integration.
# ---------------------------------------------------------------------------
AVATAR_BASE_INSTRUCTIONS = """Generate a single photo-realistic image of the person from the FIRST reference image (the headshot), naturally placed inside the scene from the SECOND reference image (if provided).

NON-NEGOTIABLE — identity preservation:
- Preserve EXACTLY the facial features, bone structure, eye shape and colour, nose, mouth, jawline, hairline, skin tone, ethnicity and apparent age of the person in the first reference photo. The face must be unmistakably the same person.
- Do NOT idealise, smooth, slim, or "beautify" the face. Keep real-world skin texture, freckles, asymmetries and proportions.

Framing, scale, and perspective (this is critical — most "pasted face" results come from breaking these rules):
- Medium shot framing: subject visible from roughly chest/waist up.
- The subject must be at REALISTIC HUMAN SCALE relative to objects in the scene. A real person standing in the room — not a portrait pasted over a wide architectural shot. Their head should look the right size next to chairs, doors, desks etc.
- Camera position: eye level with the subject, distance about 2–3 metres.
- Camera/lens character: 50mm full-frame prime equivalent, f/2.8. Subject in crisp focus; background gently out of focus with natural bokeh (NOT razor-sharp from foreground to back wall — that immediately reads as composited).
- The subject and the scene must share ONE consistent perspective and focal length.

Lighting integration (must look like ONE photo, not two):
- Lighting on the face and body must come from the visible light sources in the scene (windows, lamps, sky etc.).
- Match the scene's colour temperature (warm interior light = warm highlights on skin; cool window light = cool rim light).
- The subject's skin tones must VISIBLY pick up the warm/cool colour cast of the surrounding environment. If the room has warm wood, gold, marble, or lamp light, the face must show those warm tones — the subject's face should never feel cooler than the surrounding environment.
- Match shadow direction, softness and density across subject and background.
- Add subtle reflected/bounced light from nearby surfaces onto the subject's skin and clothing.
- Atmospheric perspective, film grain, and overall colour grade must match between subject and background.

Expression and demeanour:
- Natural relaxed expression — either a subtle, genuine soft smile OR a calm composed neutral. The subject should look approachable and present.
- Soft, alert eyes. NOT wide-eyed, NOT staring, NOT tense.
- Mouth and jaw relaxed (no clenched lips, no fake smile).
- The expression should read as "candid moment captured" rather than "posed for a photo".

Anti-compositing rules:
- No halo or unnatural edge around the subject.
- No floating subject — feet/ground/chair contact should be plausible if visible.
- No two-different-photos-mashed-together look.

Output requirements:
- One image only, realistic professional photograph aesthetic.
- NOT a 3D render, illustration, painting, or stylised image.

USER'S SCENE / STYLING REQUEST:
{user_prompt}
"""


def _build_avatar_prompt(user_prompt):
    """Wrap the user's free-form prompt with identity-preserving defaults."""
    return AVATAR_BASE_INSTRUCTIONS.format(user_prompt=(user_prompt or "").strip())


@avatar_bp.route("/")
@login_required
def index():
    return render_template("admin/avatar.html")


# ---------------------------------------------------------------------------
# Provider implementations — each must EITHER return a final R2 URL OR raise.
# ---------------------------------------------------------------------------
def _try_kie(references, prompt):
    """references: list of (bytes, filename, content_type)."""
    if not r2_storage.is_configured():
        raise RuntimeError("R2 storage isn't configured (set R2_* in .env).")

    # Kie needs URLs, so push refs to R2 first.
    ref_urls = []
    for data, name, ct in references:
        up = r2_storage.upload_bytes(data, content_type=ct, folder="avatar-refs")
        if up.get("url"):
            ref_urls.append(up["url"])
    if not ref_urls:
        raise RuntimeError("Could not upload any reference image to R2.")

    result = kie_generate_image(prompt, reference_image_url=ref_urls)
    if result.get("demo"):
        raise RuntimeError("KIE_AI_API_KEY isn't configured.")

    kie_url = result.get("image_url")
    if not kie_url:
        raise RuntimeError("Kie returned no image URL.")

    # Persist Kie's output to R2. If this fails (Kie CDN unreachable),
    # we RAISE — the caller will try the other provider.
    saved = r2_storage.upload_image(kie_url)
    final_url = saved.get("url")
    if not final_url or saved.get("demo") or "tempfile.aiquickdraw.com" in final_url:
        raise RuntimeError(
            f"Kie generated the image but its CDN is unreachable — "
            f"R2 upload failed for {kie_url[:80]}…"
        )

    return {
        "image_url": final_url,
        "provider": "kie",
        "duration": result.get("duration"),
        "cost": result.get("cost"),
        "task_id": result.get("task_id"),
    }


def _try_openai(references, prompt):
    """references: list of (bytes, filename, content_type)."""
    refs = [(data, name) for data, name, _ct in references]
    result = openai_images.generate_image_with_references(prompt, refs)
    if result.get("demo"):
        raise RuntimeError("OPENAI_API_KEY isn't configured.")
    final_url = result.get("image_url")
    if not final_url:
        raise RuntimeError("OpenAI returned no image URL.")
    return {
        "image_url": final_url,
        "provider": "openai",
        "duration": result.get("duration"),
        "cost": result.get("cost"),
        "task_id": result.get("task_id"),
    }


def _try_gemini(references, prompt):
    """references: list of (bytes, filename, content_type)."""
    refs = [(data, name, ct) for data, name, ct in references]
    result = gemini_images.generate_image_with_references(prompt, refs)
    if result.get("demo"):
        raise RuntimeError("GEMINI_API_KEY isn't configured.")
    final_url = result.get("image_url")
    if not final_url:
        raise RuntimeError("Gemini returned no image URL.")
    return {
        "image_url": final_url,
        "provider": "gemini",
        "duration": result.get("duration"),
        "cost": result.get("cost"),
        "task_id": result.get("task_id"),
    }


# ---------------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------------
@avatar_bp.route("/api/generate", methods=["POST"])
@login_required
def generate():
    primary = request.files.get("primary")
    reference = request.files.get("reference")
    prompt = (request.form.get("prompt") or "").strip()

    if not primary:
        return jsonify({"error": "Primary image is required."}), 400
    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    # Wrap the user's prompt with the always-on identity-preserving instructions.
    prompt = _build_avatar_prompt(prompt)

    # Read uploads into memory once.
    references = []
    primary_bytes = primary.read()
    if not primary_bytes:
        return jsonify({"error": "Primary file was empty."}), 400
    references.append((primary_bytes, primary.filename or "primary.png",
                       primary.mimetype or "image/jpeg"))

    if reference:
        ref_bytes = reference.read()
        if ref_bytes:
            references.append((ref_bytes, reference.filename or "reference.png",
                               reference.mimetype or "image/jpeg"))

    # Decide provider order. Configured provider tried first, others as fallback.
    primary_provider = os.environ.get("IMAGE_PROVIDER", "gemini").strip().lower()
    chains = {
        "gemini": ["gemini", "openai", "kie"],
        "openai": ["openai", "gemini", "kie"],
        "kie":    ["kie", "gemini", "openai"],
    }
    order = chains.get(primary_provider, chains["gemini"])

    impls = {"gemini": _try_gemini, "openai": _try_openai, "kie": _try_kie}

    errors = []
    for provider in order:
        impl = impls[provider]
        try:
            result = impl(references, prompt)
            if errors:  # primary failed but fallback succeeded — surface that
                result["fallback_reason"] = " | ".join(errors)
            return jsonify(result)
        except Exception as e:
            errors.append(f"{provider}: {type(e).__name__}: {e}")

    return jsonify({
        "error": "All image providers failed.",
        "details": errors,
    }), 502
