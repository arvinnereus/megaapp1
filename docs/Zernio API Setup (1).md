# CAM Lite — Student Integration Guide

Prompts and reference material for connecting your CAM Lite to external services (video generation, social media publishing). Paste these into your AI assistant (Claude, ChatGPT, etc.) to get working code.

---

## 1. Fix Slow B-Roll Video Generation (Kie.ai + Google Veo Fallback)

```
I'm building a content automation tool that generates short-form video content.
My tech stack:
- OpenRouter for LLM (script generation, prompts)
- Kie.ai for B-roll video generation (Veo 3.1 Fast model)
- I generate 5 B-roll clips per video, each 8 seconds, portrait 9:16

My problem: Kie.ai video generation takes 5-15 minutes per clip and frequently
times out. When you're generating 5 clips, that's potentially 75 minutes of
waiting — or total failure if even one times out.

Help me fix this with THREE improvements:

## 1. PARALLEL GENERATION (biggest speed win)
Right now I'm generating clips one at a time (sequential). Show me how to submit
ALL 5 Kie.ai video tasks at once, save all the task IDs, then poll them all
together. This alone cuts wait time from 5x to 1x.

Pattern:
- Submit all 5 prompts to Kie.ai → get 5 task IDs
- Poll all 5 every 30 seconds in one loop
- Collect completed URLs as they finish
- Only fail if ALL 5 fail

## 2. GOOGLE VEO DIRECT FALLBACK
Kie.ai is a middleman routing to Google's Veo model. Add a direct fallback:
- If a Kie.ai clip fails or times out after 10 minutes, retry that specific
  clip using Google's Gemini API (veo-3.1-generate) directly
- Use the google-genai Python SDK
- Environment variable: GOOGLE_GEMINI_API_KEY
- Same prompt, same 9:16 aspect ratio, same 8-second duration

## 3. PATIENT RETRY (don't give up too early)
Instead of one 15-minute timeout, use a patient retry pattern:
- Poll every 60 seconds for up to 10 minutes on Kie.ai
- If still processing at 10 min, DON'T cancel — start the Google Direct
  fallback in parallel
- Use whichever finishes first

## Technical details:
- Kie.ai API: POST to create task, GET to poll status, returns video download URL
- Google Gemini: use generate_videos() from google-genai SDK
- I want simple Python functions I can import, not classes
- Log everything: which service was used, how long each clip took, any failures
- Environment variables: KIE_AI_API_KEY, GOOGLE_GEMINI_API_KEY

## Cost awareness:
- Kie.ai Veo 3.1 Fast: ~$0.30/clip
- Google Veo Direct: ~$0.35/clip (slightly more but way more reliable)
- Only charge the fallback cost if the fallback was actually used

Show me the complete implementation with all three improvements.
```

---

## 2. Publish Directly to Social Media via Zernio API

Paste this into your AI assistant to build a complete Zernio publishing module.

```
I need to publish videos directly from my Python app to social media using the
Zernio API (zernio.com). Build me a complete publishing module.

## WHAT I HAVE
- A video URL (hosted on cloud storage like R2, S3, or Cloudinary)
- A caption/description for each platform
- Connected social accounts on Zernio

## ZERNIO API REFERENCE

**Base URL:** https://zernio.com/api/v1
**Auth:** Bearer token in Authorization header
**Env vars needed:** ZERNIO_API_KEY, ZERNIO_PROFILE_ID

### Step 1: Get connected accounts
```
GET /accounts?profileId={ZERNIO_PROFILE_ID}
Authorization: Bearer {ZERNIO_API_KEY}
```
Response: array of accounts, each has `_id`, `platform`, `displayName`
Save the `_id` for each platform — you need it to create posts.

### Step 2: Create a video post
```
POST /posts
Authorization: Bearer {ZERNIO_API_KEY}
Content-Type: application/json

{
  "content": "Your caption here",
  "scheduledFor": "2026-05-05T12:00:00",
  "platforms": [
    {"platform": "tiktok", "accountId": "the_account_id_from_step_1"}
  ],
  "mediaItems": [
    {"type": "video", "url": "https://your-cloud-storage.com/video.mp4"}
  ]
}
```

### Platform names (use these exact strings):
twitter, instagram, linkedin, tiktok, facebook, youtube, threads, pinterest

### Platform-specific settings:

**YouTube** — needs title + category inside platformSpecificData:
```json
{
  "platforms": [{
    "platform": "youtube",
    "accountId": "YOUR_YT_ACCOUNT_ID",
    "platformSpecificData": {
      "title": "Your Video Title",
      "visibility": "public",
      "madeForKids": false,
      "categoryId": 28
    }
  }]
}
```

**TikTok** — needs AI disclosure + privacy settings:
```json
{
  "tiktokSettings": {
    "video_made_with_ai": true,
    "privacy_level": "PUBLIC_TO_EVERYONE",
    "content_preview_confirmed": true,
    "express_consent_given": true,
    "allow_comment": true,
    "allow_duet": true,
    "allow_stitch": true
  }
}
```

**Instagram** — can add cover image:
```json
{
  "mediaItems": [{
    "type": "video",
    "url": "https://video-url.mp4",
    "instagramThumbnail": "https://thumbnail-url.jpg"
  }]
}
```

## WHAT I NEED YOU TO BUILD

A Python file called `publisher.py` with these functions:

1. `get_accounts(api_key, profile_id)` → returns dict mapping platform name
   to account_id (e.g., {"tiktok": "abc123", "instagram": "def456"})

2. `publish_to_all(video_url, captions, api_key, profile_id, scheduled_time=None)`
   - `captions` is a dict: {"tiktok": "...", "instagram": "...", "youtube": "...", etc.}
   - Makes SEPARATE API calls per platform so each gets its own caption
   - If scheduled_time is None, publish immediately (add "publishNow": true)
   - Adds tiktokSettings when posting to TikTok
   - Adds platformSpecificData when posting to YouTube
   - Returns dict of {platform: post_id} for tracking
   - Handles errors per-platform (one failure shouldn't stop others)
   - Retries on 429/502/503/504 with exponential backoff (3 attempts)

3. `check_status(post_id, api_key)` → GET /posts/{post_id} to verify publish

## IMPORTANT RULES
- Use httpx (not requests) for HTTP calls
- Each platform gets its OWN API call with its OWN caption
- Video URL must be publicly accessible (Zernio servers download it)
- Log which platforms succeeded/failed with the post IDs
- YouTube title comes from captions dict key "youtube_title"
- Keep it simple — one file, no classes, just functions
```

---

## Common Gotchas

| Issue | Fix |
|-------|-----|
| Zernio says "response too large" on Facebook | Keep Facebook captions under 500 characters |
| Video won't publish — 403 error | Your video URL must be publicly accessible. If using R2/S3, generate a presigned URL with 7-day expiry |
| TikTok post rejected | You MUST include `tiktokSettings` with `privacy_level` and consent fields |
| YouTube post has no title | YouTube requires `platformSpecificData.title` inside the platform object |
| Captions are the same on every platform | Make SEPARATE API calls per platform, not one call with multiple platforms |
| Kie.ai times out after 15 min | Use the parallel generation + Google Veo Direct fallback pattern above |
| Video generation takes 75 min for 5 clips | You're generating sequentially. Submit all 5 at once, poll together |

---

## Environment Variables Needed

```bash
# LLM
OPENROUTER_API_KEY=your_key

# Video Generation
KIE_AI_API_KEY=your_key
GOOGLE_GEMINI_API_KEY=your_key          # Fallback for Veo Direct

# Publishing
ZERNIO_API_KEY=your_key                 # Get from zernio.com/dashboard/api-keys
ZERNIO_PROFILE_ID=your_profile_id       # Found in Zernio dashboard URL or account settings
```

---

*Built by the Jonathan Acuna. Questions? Post in the group.*
