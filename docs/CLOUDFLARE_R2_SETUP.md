# Cloudflare R2 Storage Setup Guide

Complete guide to setting up Cloudflare R2 for content automation pipelines. R2 is S3-compatible object storage with **zero egress fees**, making it ideal for video/image hosting where external services (HeyGen, Kie.ai, GetLate, Shotstack) need to download your files.

---

## Why R2 for Content Automation

| Feature | R2 | S3 | Cloudinary |
|---------|----|----|------------|
| Egress (download) fees | **$0** | $0.09/GB | Included in plan |
| Storage cost | $0.015/GB/mo | $0.023/GB/mo | $99/mo for 100GB |
| 10GB/month cost | **~$0.15** | ~$0.23 + egress | $99 |
| S3 API compatible | Yes | Yes | No |
| Presigned URLs | Yes | Yes | N/A |
| CDN included | Yes (Cloudflare edge) | No (need CloudFront) | Yes |

For a content automation pipeline producing 30+ videos/month with B-roll, thumbnails, audio, and final composites, R2 costs pennies versus $99+/month on Cloudinary.

---

## Step 1: Create a Cloudflare Account

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com/)
2. Sign up for a free account (no credit card needed for R2 free tier)
3. Free tier includes: **10GB storage, 10 million reads, 1 million writes per month**

---

## Step 2: Create an R2 Bucket

1. In the Cloudflare dashboard, click **R2 Object Storage** in the left sidebar
2. Click **Create bucket**
3. Name it something descriptive: `cam-media`, `content-pipeline`, or `your-brand-media`
4. Select **Automatic** for location (Cloudflare picks the closest region)
5. Click **Create bucket**

### Naming Rules
- Lowercase letters, numbers, and hyphens only
- 3-63 characters
- Must start with a letter or number
- Example: `cam-media-production`

---

## Step 3: Enable Public Access

Your bucket needs a public URL so external services can access files.

1. Go to your bucket's **Settings** tab
2. Scroll to **Public access**
3. Under **R2.dev subdomain**, click **Allow Access**
4. You'll get a URL like: `https://pub-abc123def456.r2.dev`
5. Copy this URL - this is your `R2_PUBLIC_URL`

### Optional: Custom Domain (Recommended for Production)

A custom domain like `media.yourbrand.com` looks more professional and avoids the `r2.dev` identifier:

1. In bucket Settings > **Custom domains**, click **Connect Domain**
2. Enter your subdomain: `media.yourbrand.com`
3. Cloudflare automatically configures DNS and SSL
4. Update `R2_PUBLIC_URL` to use the custom domain

> **Important:** Both r2.dev and custom domain URLs are subject to Cloudflare's WAF/bot protection. Server-to-server requests (from HeyGen, Kie.ai, GetLate, etc.) will get HTTP 403. That's why the pipeline uses **presigned URLs** for all external service calls. See the "Presigned URLs" section below.

---

## Step 4: Create an API Token

1. In the R2 dashboard, click **Manage R2 API Tokens** (top-right)
2. Click **Create API token**
3. Configure the token:
   - **Token name:** `CAM Pipeline` (or whatever you prefer)
   - **Permissions:** Object Read & Write
   - **Specify bucket(s):** Select your bucket (or "Apply to all buckets" if you prefer)
   - **TTL:** Optional (leave blank for no expiration)
4. Click **Create API Token**
5. **SAVE THESE VALUES IMMEDIATELY** (they're shown only once):
   - **Access Key ID** → `R2_ACCESS_KEY_ID`
   - **Secret Access Key** → `R2_SECRET_ACCESS_KEY`

### Finding Your Account ID

Your Account ID is in the URL when you're on the R2 page:
```
https://dash.cloudflare.com/{ACCOUNT_ID}/r2/overview
```

Or: R2 Overview page > right sidebar > **Account ID**

This is your `R2_ACCOUNT_ID`.

---

## Step 5: Configure Environment Variables

Add these to your `.env` file:

```env
# Storage provider selection
STORAGE_PROVIDER=r2

# Cloudflare R2 credentials
R2_ACCOUNT_ID=your-32-char-account-id
R2_ACCESS_KEY_ID=your-access-key-id
R2_SECRET_ACCESS_KEY=your-secret-access-key
R2_BUCKET_NAME=cam-media
R2_PUBLIC_URL=https://pub-abc123def456.r2.dev
```

### Where to Find Each Value

| Variable | Where to Find It |
|----------|-----------------|
| `R2_ACCOUNT_ID` | Dashboard URL or R2 Overview sidebar (32-character hex string) |
| `R2_ACCESS_KEY_ID` | Shown when you create the API token |
| `R2_SECRET_ACCESS_KEY` | Shown when you create the API token (only shown once!) |
| `R2_BUCKET_NAME` | The name you chose in Step 2 |
| `R2_PUBLIC_URL` | Bucket Settings > Public access > R2.dev subdomain URL |

---

## Step 6: Verify Connection

In CAM, go to **Settings** and click the **Test** button next to R2 Storage. It should return "Connected to R2 bucket: your-bucket-name".

Or test via Python:
```python
from app.services.r2_storage import R2StorageService
r2 = R2StorageService()
print(r2.test_connection())
# {'success': True, 'message': 'Connected to R2 bucket: cam-media'}
```

---

## Folder Structure (Best Practices)

The pipeline automatically organizes files into folders by type:

```
your-bucket/
├── audio/              # Voice-over audio files (ElevenLabs/Fish.audio output)
│   ├── audio-a1b2c3d4.mp3
│   └── audio-e5f6g7h8.mp3
│
├── videos/             # Intermediate video files
│   ├── video-i9j0k1l2.mp4    # HeyGen avatar clips
│   └── video-m3n4o5p6.mp4    # B-roll clips from Kie.ai
│
├── final_videos/       # Composited output (Shotstack renders)
│   ├── video-q7r8s9t0.mp4    # Ready-to-publish final videos
│   └── video-u1v2w3x4.mp4
│
├── images/             # Thumbnails, headshots, character sheets
│   ├── image-y5z6a7b8.png    # AI-generated thumbnails
│   └── image-c9d0e1f2.jpg    # Uploaded headshots
│
├── carousel/           # Multi-image carousel slides
│   └── image-g3h4i5j6.png
│
└── music/              # Background music tracks
    └── track-k7l8m9n0.mp3
```

### Key Points

- **Files are never overwritten.** Every upload gets a UUID suffix (e.g., `video-a1b2c3d4.mp4`) to prevent collisions.
- **Folder names are hardcoded by file type** in the pipeline. Don't rename them.
- **Final videos** go to `final_videos/` because Shotstack render URLs expire in 24-48 hours. The pipeline downloads and re-uploads to R2 for permanent storage.
- **No nested subfolders** per client/date — the UUID in the filename is the unique identifier. The content database tracks which files belong to which content item.

---

## Presigned URLs (Critical for External Services)

### The Problem

Cloudflare's WAF/bot protection blocks server-to-server downloads on both `r2.dev` and custom domain URLs. When HeyGen, Kie.ai, GetLate, or Shotstack try to download a file from your R2 bucket, they get HTTP 403 Forbidden.

### The Solution

Presigned URLs authenticate directly against the S3 API endpoint, bypassing Cloudflare's edge entirely. They have an expiration time and are safe to share with external services.

```python
from app.services.r2_storage import R2StorageService
r2 = R2StorageService()

# Convert any R2 public URL to a presigned URL
presigned = r2.to_presigned("https://pub-abc123.r2.dev/audio/audio-xyz.mp3")
# Returns: https://account-id.r2.cloudflarestorage.com/bucket/audio/audio-xyz.mp3?X-Amz-...

# With custom expiry (default is 7 days = 604800 seconds, the max R2 allows)
presigned = r2.to_presigned(url, expires_in=3600)  # 1 hour
```

### Rules for Presigned URLs

1. **Maximum expiry: 7 days (604800 seconds)** — R2's hard limit
2. **Always presign before sending to external services** — HeyGen, Kie.ai, GetLate, Shotstack all need presigned URLs
3. **For scheduled publishing (GetLate):** Use `expires_in=604800` (7 days). If content is scheduled more than 7 days out, URLs need regeneration at publish time
4. **Non-R2 URLs pass through unchanged** — `to_presigned()` only converts URLs matching your R2 domain

### Adding Presigned URL Support to New Services

When integrating a new external service that receives R2 URLs, add this pattern:

```python
def _make_url_accessible(self, url: str) -> str:
    """Convert R2 URLs to presigned URLs for external service access."""
    if not url:
        return url
    try:
        from app.services.r2_storage import R2StorageService
        r2 = R2StorageService()
        return r2.to_presigned(url, expires_in=604800)
    except Exception:
        return url  # Fall back to original URL
```

---

## CORS Configuration (If Needed)

If you're building a web app that uploads directly from the browser to R2, configure CORS:

1. Go to your bucket's **Settings** tab
2. Under **CORS policy**, add:

```json
[
  {
    "AllowedOrigins": ["https://yourdomain.com"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }
]
```

> CAM doesn't need CORS because all uploads go through the server (boto3), not the browser.

---

## Cost Breakdown

### Free Tier (no credit card)
- 10 GB storage
- 10 million Class B operations (reads) per month
- 1 million Class A operations (writes) per month

### Paid Tier (after free tier)
- Storage: $0.015/GB/month
- Class A (writes): $4.50 per million
- Class B (reads): $0.36 per million
- Egress: **$0.00** (always free)

### Real-World Example (30 videos/month)

| Asset | Count | Avg Size | Total |
|-------|-------|----------|-------|
| Audio files | 30 | 1 MB | 30 MB |
| Avatar clips | 60 | 5 MB | 300 MB |
| B-roll clips | 150 | 10 MB | 1.5 GB |
| Final videos | 30 | 15 MB | 450 MB |
| Thumbnails | 30 | 0.5 MB | 15 MB |
| **Total/month** | | | **~2.3 GB** |

**Monthly cost: ~$0.03** (well within free tier)

After 4 months of accumulation (~10 GB): still free tier. After that, ~$0.15/month.

---

## Troubleshooting

### "Access Denied" or 403 errors
- Verify `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` are correct
- Check that the API token has Read & Write permissions
- Confirm the token is scoped to the correct bucket

### "NoSuchBucket" error
- Check `R2_BUCKET_NAME` matches exactly (case-sensitive)
- Verify the bucket exists in the correct Cloudflare account

### External services get 403 on R2 URLs
- This is expected. Use presigned URLs (see above)
- Check that `R2_ACCOUNT_ID` is correct (used in the S3 endpoint URL)

### "SignatureDoesNotMatch" error
- `R2_SECRET_ACCESS_KEY` is wrong or was copied with trailing whitespace
- Regenerate the API token and update the key

### Files upload but URL returns 404
- Check `R2_PUBLIC_URL` matches the R2.dev subdomain shown in bucket settings
- If using a custom domain, ensure DNS is configured and SSL is active

### Presigned URLs expire too fast
- Default is 7 days (604800s), which is R2's maximum
- For content scheduled further out, URLs need regeneration at publish time
- Check `expires_in` parameter in your presign calls

---

## Security Best Practices

1. **Never expose R2 credentials in client-side code** — all uploads go through your server
2. **Use scoped API tokens** — limit to specific buckets, not the entire account
3. **Rotate tokens periodically** — create a new token, update `.env`, delete the old one
4. **Presigned URL expiry** — use the shortest expiry that works for your use case (1 hour for immediate use, 7 days for scheduled publishing)
5. **Path traversal protection** — the R2 service rejects keys containing `..` or starting with `/`
6. **Don't commit `.env` to git** — it's in `.gitignore` for a reason

---

## Quick Reference: Environment Variables

```env
STORAGE_PROVIDER=r2
R2_ACCOUNT_ID=32-character-hex-string
R2_ACCESS_KEY_ID=from-api-token-creation
R2_SECRET_ACCESS_KEY=from-api-token-creation
R2_BUCKET_NAME=your-bucket-name
R2_PUBLIC_URL=https://pub-xxx.r2.dev
```
