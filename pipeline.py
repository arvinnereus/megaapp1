"""
pipeline.py — Pipeline Orchestrator
======================================
This is the CORE of the app. It runs the 6-stage content automation pipeline
and emits SSE events at every step so the "Automation X-ray" can visualize it.

Pipeline stages:
  1. scrape   — FireCrawl (skip if input_type='idea')
  2. script   — OpenRouter LLM generates post text
  3. image    — Kie.ai Nano Banana Pro generates image
  4. video    — Kie.ai Veo 3.1 generates video (optional)
  5. caption  — OpenRouter LLM generates platform-specific captions
  6. publish  — GetLate.dev posts to social media (only when explicitly triggered)

Each stage:
  - Updates the content_item status in the database
  - Logs to pipeline_logs
  - Emits SSE events via the emit_event callback
  - Tracks duration and cost
"""

import json
import os
import time
from datetime import datetime

from models import ContentItem, PipelineLog, Setting
from extensions import db
from services.firecrawl import scrape_url
from services.openrouter import generate_script, generate_image_prompt, generate_captions
from services.openai_images import generate_image
from services.kie_ai import generate_video, generate_video_with_reference
from services.getlate import publish_post
from services.r2_storage import upload_image as r2_upload_image, upload_video as r2_upload_video, is_configured as r2_is_configured


# ---------------------------------------------------------------------------
# Helper: record per-stage duration and cost as JSON on content item
# ---------------------------------------------------------------------------
def _record_stage_metric(content_id, stage_name, duration=0.0, cost=0.0):
    """
    Append a stage's duration and cost to the JSON blobs stored on the content item.
    Reads existing stage_durations / stage_costs (or starts from {}), adds the new
    values, and writes back.
    """
    item = db.session.get(ContentItem, content_id)
    if not item:
        return

    # Parse existing JSON or start fresh
    try:
        durations = json.loads(item.stage_durations or "{}")
    except (json.JSONDecodeError, TypeError):
        durations = {}
    try:
        costs = json.loads(item.stage_costs or "{}")
    except (json.JSONDecodeError, TypeError):
        costs = {}

    durations[stage_name] = duration
    costs[stage_name] = cost

    item.stage_durations = json.dumps(durations)
    item.stage_costs = json.dumps(costs)
    db.session.commit()


# ---------------------------------------------------------------------------
# Internal helper: add a pipeline log entry
# ---------------------------------------------------------------------------
def _add_log(content_id, stage, status, message, detail=None):
    log = PipelineLog(
        content_id=content_id,
        stage=stage,
        status=status,
        message=message,
        detail=detail,
    )
    db.session.add(log)
    db.session.commit()


# ---------------------------------------------------------------------------
# run_pipeline() — Execute stages 1-5 (everything except publish)
# ---------------------------------------------------------------------------
def run_pipeline(content_id, emit_event):
    """
    Run the full content pipeline for a content item.
    Executes stages 1-5 sequentially, emitting SSE events at each step.

    Stage 6 (publish) is NOT run here — it's triggered separately via /api/publish/<id>.

    Args:
        content_id: ID of the content_item to process
        emit_event: Callback function(stage, status, message, detail=None)
    """
    # Load the content item
    item = db.session.get(ContentItem, content_id)
    if not item:
        emit_event("pipeline", "error", f"Content item {content_id} not found")
        return

    total_cost = 0.0
    pipeline_start = time.time()

    emit_event("pipeline", "started",
               f"Kicking off your content machine! We'll turn your {'link' if item.input_type == 'url' else 'idea'} into a ready-to-post piece of content.",
               {"content_id": content_id, "input_type": item.input_type})

    try:
        # ==================================================================
        # STAGE 1: SCRAPE — Fetch article from URL (skip if 'idea')
        # ==================================================================
        cost = stage_scrape(content_id, item, emit_event)
        total_cost += cost
        # Reload item to get updated fields
        item = db.session.get(ContentItem, content_id)

        # ==================================================================
        # STAGE 2: SCRIPT — Generate social media post text
        # ==================================================================
        cost = stage_script(content_id, item, emit_event)
        total_cost += cost
        item = db.session.get(ContentItem, content_id)

        # ==================================================================
        # STAGE 3: IMAGE — Generate image with Kie.ai
        # ==================================================================
        cost = stage_image(content_id, item, emit_event)
        total_cost += cost
        item = db.session.get(ContentItem, content_id)

        # ==================================================================
        # STAGE 4: VIDEO — Generate video (optional)
        # ==================================================================
        cost = stage_video(content_id, item, emit_event)
        total_cost += cost
        item = db.session.get(ContentItem, content_id)

        # ==================================================================
        # STAGE 5: CAPTION — Generate platform-specific captions
        # ==================================================================
        cost = stage_caption(content_id, item, emit_event)
        total_cost += cost
        item = db.session.get(ContentItem, content_id)

        # ==================================================================
        # STAGE 6: R2 UPLOAD
        # ==================================================================
        cost = stage_r2_upload(content_id, item, emit_event)
        total_cost += cost
        item = db.session.get(ContentItem, content_id)

        # ==================================================================
        # PIPELINE COMPLETE
        # ==================================================================
        total_duration = round(time.time() - pipeline_start, 1)

        item = db.session.get(ContentItem, content_id)
        item.status = "ready"
        item.cost_total = total_cost
        db.session.commit()

        emit_event("pipeline", "complete",
                   f"All done! Your content is ready to post. The whole thing took {total_duration}s and cost ${total_cost:.4f}. That's the power of automation — what would take you an hour, the machine did in under a minute.",
                   {"total_duration": total_duration, "total_cost": total_cost})

    except Exception as e:
        # If any stage fails, mark the item as failed
        item = db.session.get(ContentItem, content_id)
        if item:
            item.status = "failed"
            db.session.commit()
        error_msg = str(e)
        if "timed out" in error_msg.lower():
            friendly = f"Pipeline stopped: {error_msg}"
        else:
            friendly = f"Something went wrong: {error_msg}. Check your API keys in Settings, or try again in a few minutes."
        emit_event("pipeline", "error", friendly, {"error": error_msg})


# ---------------------------------------------------------------------------
# STAGE 1: SCRAPE
# ---------------------------------------------------------------------------
def stage_scrape(content_id, item, emit_event):
    """Scrape article from URL. Skip if input_type is 'idea'."""
    stage = "scrape"

    if item.input_type != "url":
        emit_event(stage, "skipped", "You typed an idea (not a link), so we don't need to go grab an article from the internet. Skipping this step!")
        _add_log(content_id, stage, "skipped", "Input is an idea, no URL to scrape")
        return 0.0

    start = time.time()
    emit_event(stage, "started", "Sending your link to FireCrawl — it will visit the webpage and pull out just the article text (no ads, no menus, just the good stuff).")
    _add_log(content_id, stage, "started", f"Scraping: {item.input_text}")

    row = db.session.get(ContentItem, content_id)
    row.status = "scraping"
    db.session.commit()

    result = scrape_url(item.input_text, emit_event=emit_event)

    duration = round(time.time() - start, 1)

    # Save scraped content to database
    row = db.session.get(ContentItem, content_id)
    row.status = "scraped"
    row.article_text = result["markdown"]
    row.article_title = result.get("title", "")
    row.word_count = result.get("word_count", 0)
    db.session.commit()

    detail = {
        "duration": duration,
        "word_count": result.get("word_count", 0),
        "title": result.get("title", ""),
        "demo": result.get("demo", False),
        "cost": 0.0
    }

    emit_event(stage, "complete",
               f"Got it! FireCrawl pulled {result.get('word_count', 0):,} words from the article in {duration}s. Now we'll send this text to AI to turn it into a post.",
               detail)
    _add_log(content_id, stage, "complete",
             f"Scraped {result.get('word_count', 0)} words", json.dumps(detail))

    _record_stage_metric(content_id, stage, duration=duration, cost=0.0)
    return 0.0  # FireCrawl cost is tracked per-account, not per-call


# ---------------------------------------------------------------------------
# STAGE 2: SCRIPT
# ---------------------------------------------------------------------------
def stage_script(content_id, item, emit_event):
    """Generate social media post script via LLM."""
    stage = "script"
    start = time.time()

    emit_event(stage, "started", f"Sending your content to AI (via OpenRouter) to write a {item.platform} post. Think of OpenRouter as a switchboard — it picks the best AI model for the job.")
    _add_log(content_id, stage, "started", "Calling OpenRouter LLM")

    row = db.session.get(ContentItem, content_id)
    row.status = "scripting"
    db.session.commit()

    # Use article text if available, otherwise use the raw input
    source_text = item.article_text or item.input_text
    input_type = item.input_type

    result = generate_script(
        source_text,
        platform=item.platform,
        input_type=input_type,
        emit_event=emit_event
    )

    duration = round(time.time() - start, 1)

    # Save script to database
    row = db.session.get(ContentItem, content_id)
    row.status = "scripted"
    row.script = result["text"]
    db.session.commit()

    detail = {
        "duration": duration,
        "model": result.get("model", ""),
        "tokens_in": result.get("tokens_in", 0),
        "tokens_out": result.get("tokens_out", 0),
        "cost": result.get("cost", 0.0),
        "demo": result.get("demo", False)
    }

    emit_event(stage, "complete",
               f"Script is done! The AI wrote {result.get('tokens_out', 0)} tokens (words/pieces) in {duration}s. Cost: ${result.get('cost', 0):.4f}. Next up: creating a matching image.",
               detail)
    _add_log(content_id, stage, "complete",
             f"Script: {result.get('tokens_out', 0)} tokens", json.dumps(detail))

    cost = result.get("cost", 0.0)
    _record_stage_metric(content_id, stage, duration=duration, cost=cost)
    return cost


# ---------------------------------------------------------------------------
# STAGE 3: IMAGE
# ---------------------------------------------------------------------------
def stage_image(content_id, item, emit_event):
    """Generate image: first create a prompt via LLM, then generate via Kie.ai."""
    stage = "image"
    start = time.time()

    emit_event(stage, "started", "Time to create an image! First, AI will describe what the image should look like (a 'prompt'). Then we send that description to Kie.ai, which actually draws the picture.")
    _add_log(content_id, stage, "started", "Generating image prompt + image")

    row = db.session.get(ContentItem, content_id)
    row.status = "imaging"
    db.session.commit()

    # Step 1: Generate an image prompt from the script
    prompt_result = generate_image_prompt(item.script or "", emit_event=emit_event)
    image_prompt = prompt_result["text"]

    # Save the prompt
    row = db.session.get(ContentItem, content_id)
    row.image_prompt = image_prompt
    db.session.commit()

    # Step 2: Generate the actual image via Kie.ai (with headshot reference if available)
    headshot_url = Setting.get("HEADSHOT_URL")
    if headshot_url and headshot_url.startswith("http"):
        image_result = generate_image(image_prompt, emit_event=emit_event, reference_image_url=headshot_url)
    else:
        image_result = generate_image(image_prompt, emit_event=emit_event)

    duration = round(time.time() - start, 1)

    # Save image URL and task ID
    row = db.session.get(ContentItem, content_id)
    row.status = "imaged"
    row.image_url = image_result.get("image_url", "")
    row.image_task_id = image_result.get("task_id", "")
    db.session.commit()

    # Total cost = LLM prompt cost + image generation cost
    total_cost = prompt_result.get("cost", 0.0) + image_result.get("cost", 0.0)

    detail = {
        "duration": duration,
        "image_url": image_result.get("image_url", ""),
        "task_id": image_result.get("task_id", ""),
        "prompt_cost": prompt_result.get("cost", 0.0),
        "image_cost": image_result.get("cost", 0.0),
        "total_cost": total_cost,
        "demo": image_result.get("demo", False)
    }

    emit_event(stage, "complete",
               f"Image is ready! It took {duration}s because Kie.ai had to actually render the picture (that's why we kept checking on it). Cost: ${total_cost:.4f}.",
               detail)
    _add_log(content_id, stage, "complete",
             f"Image ready: {image_result.get('task_id', 'N/A')}", json.dumps(detail))

    _record_stage_metric(content_id, stage, duration=duration, cost=total_cost)
    return total_cost


# ---------------------------------------------------------------------------
# STAGE 4: VIDEO (optional)
# ---------------------------------------------------------------------------
def stage_video(content_id, item, emit_event):
    """Generate video via Kie.ai. Skip if include_video is False. Supports headshot toggle."""
    stage = "video"

    if not item.include_video:
        emit_event(stage, "skipped", "You didn't ask for a video this time, so we're skipping this step. (Videos take longer and cost more — you can turn this on anytime!)")
        _add_log(content_id, stage, "skipped", "include_video is False")
        return 0.0

    start = time.time()
    emit_event(stage, "started", "Creating a video with Kie.ai's Veo model. This takes longer than images (sometimes a few minutes) because video has way more frames to generate. Watch the polling — we keep asking 'is it done yet?' every 20 seconds.")
    _add_log(content_id, stage, "started", "Calling Kie.ai Veo 3.1")

    row = db.session.get(ContentItem, content_id)
    row.status = "videoing"
    db.session.commit()

    # Use the image prompt as the video prompt (with slight modification)
    video_prompt = item.image_prompt or item.script or ""
    row = db.session.get(ContentItem, content_id)
    row.video_prompt = video_prompt
    db.session.commit()

    # Check headshot — use HEADSHOT_URL from Settings
    headshot_url = Setting.get("HEADSHOT_URL")

    if headshot_url and headshot_url.startswith("http"):
        emit_event(stage, "info", "Headshot reference detected — generating video with your face for a personal touch.")
        video_result = generate_video_with_reference(video_prompt, headshot_url, emit_event=emit_event)
        row = db.session.get(ContentItem, content_id)
        row.headshot_used = True
        db.session.commit()
    else:
        video_result = generate_video(video_prompt, emit_event=emit_event)

    duration = round(time.time() - start, 1)

    # Handle graceful timeout: log warning but continue to caption stage
    if video_result.get("timed_out"):
        emit_event(stage, "warning", "Video generation timed out — moving on to captions. You can re-run the video stage separately once it finishes processing.")
        _add_log(content_id, stage, "warning", "Video timed out — skipping gracefully")
        row = db.session.get(ContentItem, content_id)
        row.status = "captioned"
        row.video_task_id = video_result.get("task_id", "")
        db.session.commit()
        _record_stage_metric(content_id, stage, duration=duration, cost=0.0)
        return 0.0

    row = db.session.get(ContentItem, content_id)
    row.status = "videoed"
    row.video_url = video_result.get("video_url", "")
    row.video_task_id = video_result.get("task_id", "")
    db.session.commit()

    cost = video_result.get("cost", 0.0)

    detail = {
        "duration": duration,
        "video_url": video_result.get("video_url", ""),
        "task_id": video_result.get("task_id", ""),
        "cost": cost,
        "demo": video_result.get("demo", False)
    }

    emit_event(stage, "complete",
               f"Video is done! Took {duration}s (see how much longer than the image?). Cost: ${cost:.4f}. Almost there — just need captions now.",
               detail)
    _add_log(content_id, stage, "complete",
             f"Video ready: {video_result.get('task_id', 'N/A')}", json.dumps(detail))

    _record_stage_metric(content_id, stage, duration=duration, cost=cost)
    return cost


# ---------------------------------------------------------------------------
# STAGE 5: CAPTION
# ---------------------------------------------------------------------------
def stage_caption(content_id, item, emit_event):
    """Generate platform-specific captions via LLM."""
    stage = "caption"
    start = time.time()

    row = db.session.get(ContentItem, content_id)
    row.status = "captioning"
    db.session.commit()

    # Generate captions for the target platform + a few extras
    target = item.platform or "instagram"
    platforms = list(set([target, "instagram", "tiktok", "linkedin"]))

    emit_event(stage, "started", f"Last step! Each social platform has different rules (character limits, hashtag styles, tone). We're asking AI to write custom captions for {', '.join(platforms)} so each one fits perfectly.")
    _add_log(content_id, stage, "started", "Calling OpenRouter for captions")

    result = generate_captions(
        item.script or "",
        platforms=platforms,
        emit_event=emit_event
    )

    duration = round(time.time() - start, 1)

    # Save captions as JSON
    captions_json = json.dumps(result.get("captions", {}))
    row = db.session.get(ContentItem, content_id)
    row.status = "captioned"
    row.captions = captions_json
    db.session.commit()

    cost = result.get("cost", 0.0)

    detail = {
        "duration": duration,
        "platforms": platforms,
        "cost": cost,
        "demo": result.get("demo", False)
    }

    emit_event(stage, "complete",
               f"Captions ready for {len(platforms)} platforms in {duration}s! Each one is tailored — different length, tone, and hashtags for each platform.",
               detail)
    _add_log(content_id, stage, "complete",
             f"Captions for {len(platforms)} platforms", json.dumps(detail))

    _record_stage_metric(content_id, stage, duration=duration, cost=cost)
    return cost


# ---------------------------------------------------------------------------
# STAGE 6: R2 UPLOAD (optional — uploads assets to Cloudflare R2)
# ---------------------------------------------------------------------------
def stage_r2_upload(content_id, item, emit_event):
    """Upload image/video to Cloudflare R2 for permanent storage. Skips if R2 not configured."""
    stage = "r2_upload"

    if not r2_is_configured():
        emit_event(stage, "skipped", "R2 storage is not configured — skipping cloud upload. Your images/videos will use the original API URLs (which may expire). Add R2 credentials in Settings for permanent hosting.")
        _add_log(content_id, stage, "skipped", "R2 not configured")
        return 0.0

    start = time.time()
    emit_event(stage, "started", "Uploading your assets to Cloudflare R2 for permanent storage. API-generated URLs can expire, so we save copies to your own cloud bucket.")
    _add_log(content_id, stage, "started", "Uploading to R2")

    row = db.session.get(ContentItem, content_id)
    row.status = "uploading"
    db.session.commit()

    r2_image_url = None
    r2_video_url = None
    image_error = None
    video_error = None

    r2_public_base = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")

    # Upload image if it exists and is not a placeholder
    image_url = item.image_url or ""
    if image_url and "placeholder" not in image_url:
        if r2_public_base and image_url.startswith(r2_public_base):
            # Provider already wrote directly to our R2 (e.g. OpenAI gpt-image-1).
            r2_image_url = image_url
            emit_event(stage, "progress", "Image is already hosted on R2 — no re-upload needed.")
        else:
            try:
                img_result = r2_upload_image(image_url, emit_event=emit_event)
                r2_image_url = img_result.get("url")
            except Exception as e:
                image_error = f"{type(e).__name__}: {e}"
                emit_event(stage, "warning", f"Image upload to R2 failed: {image_error}")
                _add_log(content_id, stage, "warning", f"Image upload failed: {image_error}")

    # Upload video if it exists and is not a placeholder
    video_url = item.video_url or ""
    if video_url and "placeholder" not in video_url:
        if r2_public_base and video_url.startswith(r2_public_base):
            r2_video_url = video_url
            emit_event(stage, "progress", "Video is already hosted on R2 — no re-upload needed.")
        else:
            try:
                vid_result = r2_upload_video(video_url, emit_event=emit_event)
                r2_video_url = vid_result.get("url")
            except Exception as e:
                video_error = f"{type(e).__name__}: {e}"
                emit_event(stage, "warning", f"Video upload to R2 failed: {video_error}")
                _add_log(content_id, stage, "warning", f"Video upload failed: {video_error}")

    duration = round(time.time() - start, 1)

    row = db.session.get(ContentItem, content_id)
    row.r2_image_url = r2_image_url
    row.r2_video_url = r2_video_url
    db.session.commit()

    # Decide what to report. If anything was attempted but produced no R2 URL,
    # surface that honestly instead of claiming a clean "complete".
    image_expected = bool(image_url and "placeholder" not in image_url)
    video_expected = bool(video_url and "placeholder" not in video_url)
    image_ok = (not image_expected) or bool(r2_image_url)
    video_ok = (not video_expected) or bool(r2_video_url)
    all_ok = image_ok and video_ok

    detail = {
        "duration": duration,
        "r2_image_url": r2_image_url,
        "r2_video_url": r2_video_url,
        "image_error": image_error,
        "video_error": video_error,
        "cost": 0.0,
    }

    if all_ok:
        emit_event(stage, "complete",
                   f"Assets uploaded to R2 in {duration}s. Your content now has permanent URLs that won't expire.",
                   detail)
        _add_log(content_id, stage, "complete", "Uploaded to R2", json.dumps(detail))
    else:
        missing = []
        if image_expected and not r2_image_url:
            missing.append("image")
        if video_expected and not r2_video_url:
            missing.append("video")
        msg = (f"R2 upload finished with problems after {duration}s — "
               f"{', '.join(missing)} could NOT be saved to R2. The card will fall back to the "
               f"original (temporary) URL, which may not load if the upstream CDN is unreachable.")
        emit_event(stage, "warning", msg, detail)
        _add_log(content_id, stage, "warning", msg, json.dumps(detail))

    _record_stage_metric(content_id, stage, duration=duration, cost=0.0)
    return 0.0


# ---------------------------------------------------------------------------
# STAGE 7: PUBLISH (triggered separately)
# ---------------------------------------------------------------------------
def stage_publish(content_id, emit_event):
    """
    Publish content via GetLate.dev.
    This is NOT called by run_pipeline() — it's triggered separately
    via the /api/publish/<id> endpoint.
    """
    stage = "publish"
    start = time.time()

    item = db.session.get(ContentItem, content_id)
    if not item:
        emit_event(stage, "error", f"Content item {content_id} not found")
        return

    emit_event(stage, "started", "Publishing to social media...")
    _add_log(content_id, stage, "started", "Calling GetLate.dev API")

    item.status = "publishing"
    db.session.commit()

    try:
        result = publish_post(item, emit_event=emit_event)

        duration = round(time.time() - start, 1)

        item = db.session.get(ContentItem, content_id)
        item.status = "published"
        item.published_at = datetime.utcnow()
        db.session.commit()

        detail = {
            "duration": duration,
            "post_id": result.get("post_id", ""),
            "platforms": result.get("platforms_published", []),
            "demo": result.get("demo", False)
        }

        emit_event(stage, "complete",
                   f"Published in {duration}s!",
                   detail)
        _add_log(content_id, stage, "complete",
                 f"Published: {result.get('post_id', 'N/A')}", json.dumps(detail))

    except Exception as e:
        item = db.session.get(ContentItem, content_id)
        if item:
            item.status = "failed"
            db.session.commit()
        emit_event(stage, "error", f"Publishing failed: {str(e)}")
        _add_log(content_id, stage, "error", str(e))


# ---------------------------------------------------------------------------
# regenerate_image() — Re-run just the image stage with a new/edited prompt
# ---------------------------------------------------------------------------
def regenerate_image(content_id, new_prompt, emit_event):
    """
    Regenerate the image for a content item using a new prompt.
    Called from the /api/regenerate-image/<id> endpoint.
    """
    emit_event("image", "started", "Regenerating image with updated prompt...")
    _add_log(content_id, "image", "started", "Regenerating with new prompt")

    start = time.time()

    # Save the new prompt
    row = db.session.get(ContentItem, content_id)
    if row:
        row.image_prompt = new_prompt
        db.session.commit()

    # Generate new image
    result = generate_image(new_prompt, emit_event=emit_event)

    duration = round(time.time() - start, 1)

    row = db.session.get(ContentItem, content_id)
    if row:
        row.image_url = result.get("image_url", "")
        row.image_task_id = result.get("task_id", "")
        db.session.commit()

    detail = {
        "duration": duration,
        "image_url": result.get("image_url", ""),
        "task_id": result.get("task_id", ""),
        "cost": result.get("cost", 0.0),
        "demo": result.get("demo", False)
    }

    emit_event("image", "complete",
               f"Image regenerated in {duration}s",
               detail)
    _add_log(content_id, "image", "complete",
             f"Regenerated: {result.get('task_id', 'N/A')}", json.dumps(detail))
