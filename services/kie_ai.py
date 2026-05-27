"""
services/kie_ai.py — Image + Video Generation via Kie.ai
==========================================================
Image: Nano Banana Pro — fast AI image generation
Video: Veo 3.1 — AI video generation (longer processing)

Students learn: async/polling APIs. These APIs don't return results instantly.
You create a task, then poll for the result. The X-ray shows every poll cycle.

Polling strategy:
  Images — poll every 5s, timeout after 180s (3 minutes)
  Videos — Two-Phase Patient Polling:
    Phase 1: poll every 30s for first 5 minutes (300s)
    Phase 2: poll every 60s for up to 10 more minutes
    Total max: 15 minutes (900s)
    On timeout: return gracefully with timed_out=True (no exception)
"""

import os
import re
import time
import requests

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
KIE_BASE_URL = "https://api.kie.ai/api/v1"
TASK_CREATE_URL = f"{KIE_BASE_URL}/jobs/createTask"
TASK_STATUS_URL = f"{KIE_BASE_URL}/jobs/recordInfo"
VIDEO_CREATE_URL = f"{KIE_BASE_URL}/veo/generate"
VIDEO_STATUS_URL = f"{KIE_BASE_URL}/veo/get-1080p-video"


def _clean_prompt(prompt):
    """Remove markdown formatting that confuses image/video models."""
    prompt = re.sub(r'\*\*(.+?)\*\*', r'\1', prompt)   # **bold**
    prompt = re.sub(r'__(.+?)__', r'\1', prompt)        # __bold__
    prompt = re.sub(r'\*(.+?)\*', r'\1', prompt)        # *italic*
    prompt = re.sub(r'_(.+?)_', r'\1', prompt)          # _italic_
    prompt = re.sub(r'^#+\s*', '', prompt, flags=re.MULTILINE)  # # headers
    prompt = re.sub(r'`(.+?)`', r'\1', prompt)          # `backticks`
    prompt = prompt.replace('\t', ' ')                   # tabs → spaces
    prompt = re.sub(r'\n{3,}', '\n\n', prompt)           # collapse 3+ newlines
    prompt = prompt.replace('"', "'")                    # " → '
    return prompt.strip()


def _get_headers():
    """Build auth headers for Kie.ai API."""
    api_key = os.getenv("KIE_AI_API_KEY")
    if not api_key:
        return None
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


# ---------------------------------------------------------------------------
# generate_image() — Create an image with Nano Banana Pro
# ---------------------------------------------------------------------------
def generate_image(prompt, emit_event=None, reference_image_url=None):
    """
    Generate an image using Kie.ai's Nano Banana Pro model.

    This is an ASYNC API pattern:
    1. POST to create a task → get a task_id
    2. GET to poll the task status every 5 seconds
    3. When status is "success", download the result

    Students see every poll cycle in the X-ray log.

    Args:
        prompt: Image description prompt
        emit_event: Callback for SSE logging (THIS IS KEY for the X-ray)
        reference_image_url: Optional headshot URL for face consistency

    Returns:
        dict with: image_url, task_id, duration, cost
    """
    emit = emit_event or (lambda *a, **kw: None)
    prompt = _clean_prompt(prompt)
    headers = _get_headers()

    if not headers:
        emit("image", "progress", "No Kie.ai API key set yet — showing a placeholder image. To generate real AI images, get your key from https://kie.ai and paste it in Settings > Kie.ai > API Key.")
        return {
            "image_url": "https://placehold.co/1080x1920/17181C/C7A35A?text=Add+Kie.ai+Key+in+Settings",
            "task_id": "demo_task",
            "duration": 0,
            "cost": 0.0,
            "demo": True
        }

    # -- Normalise reference images (accept either a single URL string or a list) --
    if isinstance(reference_image_url, str):
        refs = [reference_image_url]
    elif isinstance(reference_image_url, (list, tuple)):
        refs = [u for u in reference_image_url if u]
    else:
        refs = []

    # -- Step 1: Create the task --
    if refs:
        emit("image", "progress",
             f"Sending image description + {len(refs)} reference image(s) to Kie.ai. The AI will generate an image guided by the references.")
        prompt = f"This exact person from the reference photo(s), {prompt}"
    else:
        emit("image", "progress", "Sending the image description to Kie.ai. Unlike the text AI (which responds instantly), image AI takes time — so we create a 'task' and check back on it.")

    try:
        input_payload = {
            "prompt": prompt,
            "aspect_ratio": "9:16",
            "resolution": "1K"
        }
        if refs:
            input_payload["image_input"] = refs

        create_response = requests.post(
            TASK_CREATE_URL,
            headers=headers,
            json={
                "model": "nano-banana-pro",
                "input": input_payload
            },
            timeout=30
        )
        create_response.raise_for_status()
        create_data = create_response.json()

        # Kie.ai nests the taskId inside a "data" wrapper
        data = create_data.get("data") or create_data
        task_id = data.get("taskId") or data.get("task_id") or create_data.get("taskId")
        if not task_id:
            raise Exception(f"No task_id in response: {create_data}")

        emit("image", "progress", f"Task created! ID: {task_id}. Now we wait and keep checking — this is called 'polling'. Watch below as we ask 'is it ready yet?' every 5 seconds.")

    except requests.exceptions.RequestException as e:
        emit("image", "error", f"Couldn't reach Kie.ai: {str(e)}. Check your internet connection or API key.")
        raise

    # -- Step 2: Poll for completion --
    # Images poll every 5 seconds, timeout after 180 seconds (3 minutes)
    start_time = time.time()
    poll_interval = 5
    timeout = 180
    attempt = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            emit("image", "error", f"Image generation timed out after {timeout}s")
            raise Exception(f"Image generation timed out after {timeout} seconds")

        attempt += 1
        time.sleep(poll_interval)

        try:
            status_response = requests.get(
                TASK_STATUS_URL,
                headers=headers,
                params={"taskId": task_id},
                timeout=15
            )
            status_response.raise_for_status()
            status_data = status_response.json()

            # Kie.ai nests status under "data" wrapper
            data = status_data.get("data") or status_data
            state = (data.get("state") or status_data.get("state", "unknown")).lower()

            # -- Emit polling events (the X-ray magic!) --
            emit("image", "polling",
                 f"Checking on our image... attempt #{attempt} — Kie.ai says: \"{state}\" ({round(elapsed)}s so far)",
                 {"attempt": attempt, "state": state, "elapsed": round(elapsed, 1)})

            if state in ("success", "completed", "done"):
                # Extract image URL from resultJson (JSON string with resultUrls array)
                image_url = ""
                result_json_str = data.get("resultJson", "")
                if result_json_str:
                    import json
                    result_json = json.loads(result_json_str)
                    result_urls = result_json.get("resultUrls", [])
                    if result_urls:
                        image_url = result_urls[0]
                # Fallback to other possible locations
                if not image_url:
                    results = data.get("results", status_data.get("results", {}))
                    image_url = results.get("url") or results.get("image_url", "")

                duration = round(time.time() - start_time, 1)
                cost = 0.09  # Approximate cost per image

                emit("image", "progress",
                     f"The image is done! Kie.ai finished rendering it in {duration}s. Downloading the file now...")

                return {
                    "image_url": image_url,
                    "task_id": task_id,
                    "duration": duration,
                    "cost": cost,
                    "demo": False
                }

            elif state in ("failed", "failure", "error", "cancelled"):
                error_msg = data.get("errorMessage") or data.get("error") or data.get("failMsg", "Unknown error")
                emit("image", "error", f"Image generation failed: {error_msg}")
                raise Exception(f"Image generation failed: {error_msg}")

            # Otherwise keep polling (state is 'processing', 'pending', etc.)

        except requests.exceptions.RequestException as e:
            emit("image", "progress", f"Poll request failed (attempt {attempt}), retrying...")
            # Don't raise — just retry on the next poll cycle


# ---------------------------------------------------------------------------
# generate_video() — Create a video with Veo 3.1
# ---------------------------------------------------------------------------
def generate_video(prompt, emit_event=None):
    """
    Generate a video using Kie.ai's Veo 3.1 model.

    Two-Phase Patient Polling:
      Phase 1: poll every 30s for first 5 minutes (300s)
      Phase 2: poll every 60s for up to 10 more minutes
      Total max: 15 minutes (900s)
      On timeout: returns gracefully with timed_out=True (no exception raised)

    Args:
        prompt: Video description prompt
        emit_event: Callback for SSE logging

    Returns:
        dict with: video_url, task_id, duration, cost
        On timeout: dict with video_url=None, timed_out=True, message, task_id, cost
    """
    emit = emit_event or (lambda *a, **kw: None)
    prompt = _clean_prompt(prompt)
    headers = _get_headers()

    if not headers:
        emit("video", "progress", "No Kie.ai API key set yet — showing a placeholder. To generate real AI videos, get your key from https://kie.ai and paste it in Settings > Kie.ai > API Key.")
        return {
            "video_url": "https://placehold.co/1080x1920/17181C/C7A35A?text=Add+Kie.ai+Key+in+Settings",
            "task_id": "demo_video_task",
            "duration": 0,
            "cost": 0.0,
            "demo": True
        }

    # -- Step 1: Create the video task --
    emit("video", "progress", "Sending prompt to Kie.ai's Veo 3.1 video model. Videos take WAY longer than images because they have hundreds of frames to generate.")

    try:
        create_response = requests.post(
            VIDEO_CREATE_URL,
            headers=headers,
            json={
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "model": "veo3_fast"
            },
            timeout=30
        )
        create_response.raise_for_status()
        create_data = create_response.json()

        # Kie.ai nests the taskId inside a "data" wrapper
        data = create_data.get("data") or create_data
        task_id = data.get("taskId") or data.get("task_id") or create_data.get("taskId")
        if not task_id:
            raise Exception(f"No task_id in response: {create_data}")

        emit("video", "progress", f"Video task created! ID: {task_id}. Using two-phase patient polling: every 30s for the first 5 minutes, then every 60s for up to 10 more minutes.")

    except requests.exceptions.RequestException as e:
        emit("video", "error", f"Failed to create video task: {str(e)}")
        raise

    # -- Step 2: Two-Phase Patient Polling --
    PHASE_1_INTERVAL = 30   # seconds between polls in phase 1
    PHASE_1_DURATION = 300  # phase 1 lasts 5 minutes
    PHASE_2_INTERVAL = 60   # seconds between polls in phase 2
    MAX_POLL_TIME = 900      # total max: 15 minutes

    cost = 0.19  # Approximate cost per video
    elapsed = 0
    attempt = 0

    while elapsed < MAX_POLL_TIME:
        interval = PHASE_1_INTERVAL if elapsed < PHASE_1_DURATION else PHASE_2_INTERVAL
        time.sleep(interval)
        elapsed += interval
        attempt += 1

        phase_label = "Phase 1" if elapsed < PHASE_1_DURATION else "Phase 2 (patient)"
        if emit:
            emit("video", "polling", f"{phase_label} - Attempt #{attempt}... checking status ({elapsed}s elapsed)")

        try:
            status_response = requests.get(
                VIDEO_STATUS_URL,
                headers=headers,
                params={"taskId": task_id},
                timeout=15
            )
            status_response.raise_for_status()
            status_data = status_response.json()

            # Veo uses data.successFlag: 0=generating, 1=success, 2/3=failed
            data = status_data.get("data") or status_data
            success_flag = data.get("successFlag", 0) if isinstance(data, dict) else 0
            state = data.get("state", "unknown") if isinstance(data, dict) else "unknown"
            if success_flag == 1:
                state = "success"
            elif success_flag in (2, 3):
                state = "failed"
            elif success_flag == 0 and state == "unknown":
                state = "processing"

            # -- Emit detailed polling status --
            emit("video", "polling",
                 f"{phase_label} - Attempt #{attempt} — status: \"{state}\" ({elapsed}s so far). Videos can take 1-15 minutes.",
                 {"attempt": attempt, "state": state, "elapsed": elapsed})

            if state in ("success", "completed", "done"):
                # Extract video URL — Veo returns in data.response.resultUrls[]
                video_url = ""
                if data.get("response") and data["response"].get("resultUrls"):
                    video_url = data["response"]["resultUrls"][0]
                elif data.get("videoUrl"):
                    video_url = data["videoUrl"]
                # Fallback: try resultJson like images
                if not video_url:
                    import json
                    result_json_str = data.get("resultJson", "")
                    if result_json_str:
                        result_json = json.loads(result_json_str)
                        result_urls = result_json.get("resultUrls", [])
                        if result_urls:
                            video_url = result_urls[0]

                duration = elapsed

                emit("video", "progress",
                     f"Video is done! Took {duration}s — much longer than the image, right? That's normal. Downloading now...")

                return {
                    "video_url": video_url,
                    "task_id": task_id,
                    "duration": duration,
                    "cost": cost,
                    "demo": False
                }

            elif state in ("failed", "failure", "error", "cancelled"):
                error_msg = data.get("errorMessage") or data.get("errorMsg") or data.get("failMsg", "Unknown error")
                emit("video", "error", f"Video generation failed: {error_msg}")
                raise Exception(f"Video generation failed: {error_msg}")

            # Otherwise keep polling (state is 'processing', 'pending', etc.)

        except requests.exceptions.RequestException as e:
            emit("video", "progress", f"Poll request failed (attempt {attempt}), retrying...")

    # -- Timeout: return gracefully, don't raise --
    emit("video", "progress",
         "Video generation timed out after 15 minutes. Kie.ai may still be processing in the background.")
    return {
        "video_url": None,
        "timed_out": True,
        "message": "Video generation timed out after 15 minutes. Kie.ai may still be processing - check back later.",
        "task_id": task_id,
        "cost": cost,
    }


# ---------------------------------------------------------------------------
# generate_video_with_reference() — Video with headshot reference image
# ---------------------------------------------------------------------------
def generate_video_with_reference(prompt, reference_image_url, emit_event=None):
    """
    Generate a video using Veo 3.1 with a reference headshot image.

    Same two-phase patient polling as generate_video(), but includes a reference
    image so the generated video features the person from the headshot.

    Args:
        prompt: Video description prompt
        reference_image_url: URL of the headshot/reference image
        emit_event: Callback for SSE logging

    Returns:
        dict with: video_url, task_id, duration, cost
        On timeout: dict with video_url=None, timed_out=True, message, task_id, cost
    """
    emit = emit_event or (lambda *a, **kw: None)
    prompt = _clean_prompt(prompt)
    headers = _get_headers()

    if not headers:
        emit("video", "progress", "No Kie.ai API key set yet — showing a placeholder. To generate real AI videos, get your key from https://kie.ai and paste it in Settings > Kie.ai > API Key.")
        return {
            "video_url": "https://placehold.co/1080x1920/17181C/C7A35A?text=Add+Kie.ai+Key+in+Settings",
            "task_id": "demo_video_ref_task",
            "duration": 0,
            "cost": 0.0,
            "demo": True
        }

    # -- Step 1: Create the video task with reference image --
    emit("video", "progress", "Sending prompt + headshot reference to Kie.ai's Veo 3.1. The AI will generate a video featuring the person from the headshot.")

    try:
        create_response = requests.post(
            VIDEO_CREATE_URL,
            headers=headers,
            json={
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "model": "veo3_fast",
                "reference_images": [reference_image_url]
            },
            timeout=30
        )
        create_response.raise_for_status()
        create_data = create_response.json()

        data = create_data.get("data") or create_data
        task_id = data.get("taskId") or data.get("task_id") or create_data.get("taskId")
        if not task_id:
            raise Exception(f"No task_id in response: {create_data}")

        emit("video", "progress", f"Video task created with headshot reference! ID: {task_id}. Using two-phase patient polling.")

    except requests.exceptions.RequestException as e:
        emit("video", "error", f"Failed to create video task: {str(e)}")
        raise

    # -- Step 2: Two-Phase Patient Polling --
    PHASE_1_INTERVAL = 30   # seconds between polls in phase 1
    PHASE_1_DURATION = 300  # phase 1 lasts 5 minutes
    PHASE_2_INTERVAL = 60   # seconds between polls in phase 2
    MAX_POLL_TIME = 900      # total max: 15 minutes

    cost = 0.30  # Higher cost for reference video
    elapsed = 0
    attempt = 0

    while elapsed < MAX_POLL_TIME:
        interval = PHASE_1_INTERVAL if elapsed < PHASE_1_DURATION else PHASE_2_INTERVAL
        time.sleep(interval)
        elapsed += interval
        attempt += 1

        phase_label = "Phase 1" if elapsed < PHASE_1_DURATION else "Phase 2 (patient)"
        if emit:
            emit("video", "polling", f"{phase_label} - Attempt #{attempt}... checking status ({elapsed}s elapsed)")

        try:
            status_response = requests.get(
                VIDEO_STATUS_URL,
                headers=headers,
                params={"taskId": task_id},
                timeout=15
            )
            status_response.raise_for_status()
            status_data = status_response.json()

            data = status_data.get("data") or status_data
            success_flag = data.get("successFlag", 0) if isinstance(data, dict) else 0
            state = data.get("state", "unknown") if isinstance(data, dict) else "unknown"
            if success_flag == 1:
                state = "success"
            elif success_flag in (2, 3):
                state = "failed"
            elif success_flag == 0 and state == "unknown":
                state = "processing"

            emit("video", "polling",
                 f"{phase_label} - Attempt #{attempt} — status: \"{state}\" ({elapsed}s so far). Videos can take 1-15 minutes.",
                 {"attempt": attempt, "state": state, "elapsed": elapsed})

            if state in ("success", "completed", "done"):
                video_url = ""
                if data.get("response") and data["response"].get("resultUrls"):
                    video_url = data["response"]["resultUrls"][0]
                elif data.get("videoUrl"):
                    video_url = data["videoUrl"]
                if not video_url:
                    import json
                    result_json_str = data.get("resultJson", "")
                    if result_json_str:
                        result_json = json.loads(result_json_str)
                        result_urls = result_json.get("resultUrls", [])
                        if result_urls:
                            video_url = result_urls[0]

                duration = elapsed

                emit("video", "progress",
                     f"Headshot video is done! Took {duration}s. Downloading now...")

                return {
                    "video_url": video_url,
                    "task_id": task_id,
                    "duration": duration,
                    "cost": cost,
                    "demo": False
                }

            elif state in ("failed", "failure", "error", "cancelled"):
                error_msg = data.get("errorMessage") or data.get("errorMsg") or data.get("failMsg", "Unknown error")
                emit("video", "error", f"Video generation failed: {error_msg}")
                raise Exception(f"Video generation failed: {error_msg}")

        except requests.exceptions.RequestException as e:
            emit("video", "progress", f"Poll request failed (attempt {attempt}), retrying...")

    # -- Timeout: return gracefully, don't raise --
    emit("video", "progress",
         "Reference video generation timed out after 15 minutes. Kie.ai may still be processing in the background.")
    return {
        "video_url": None,
        "timed_out": True,
        "message": "Video generation timed out after 15 minutes. Kie.ai may still be processing - check back later.",
        "task_id": task_id,
        "cost": cost,
    }
