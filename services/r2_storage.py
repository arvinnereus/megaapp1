"""
Cloudflare R2 storage service for media uploads.

Handles image, video, and headshot uploads to R2-compatible S3 storage.
Falls back to demo mode (passthrough URLs) when R2 is not configured.
"""

import os
import uuid
import mimetypes
import warnings

import boto3
import requests
import urllib3


# Required env vars for R2 configuration
R2_ENV_VARS = [
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_BUCKET_NAME",
]


def is_configured():
    """Check if all required R2 environment variables are set."""
    return all(os.environ.get(var) for var in R2_ENV_VARS)


def _get_client():
    """Create a boto3 S3 client configured for Cloudflare R2."""
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
        config=boto3.session.Config(signature_version="s3v4"),
    )


def _get_public_url(key):
    """Build a public URL for an R2 object using the configured public URL base."""
    public_url = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")
    return f"{public_url}/{key}"


def _download_bytes(url, emit_event=None):
    """
    Fetch a URL's bytes with a single resilient retry.

    Some upstream CDNs (e.g. Kie.ai's tempfile host) occasionally serve a flaky
    TLS handshake. The response bytes are still trustworthy in that case, so on
    SSLError we retry once with cert verification disabled.
    """
    try:
        response = requests.get(url, timeout=60)
    except requests.exceptions.SSLError:
        if emit_event:
            emit_event("r2_upload", "warning",
                       "Upstream TLS handshake failed — retrying once without cert verification.")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(url, timeout=60, verify=False)
    response.raise_for_status()
    return response.content, response.headers.get("Content-Type", "")


def upload_image(image_url, emit_event=None):
    """
    Upload an image to R2 storage.

    If R2 is not configured, returns a demo-mode response with the original URL.
    """
    if not is_configured():
        return {"url": image_url, "key": None, "demo": True}

    if emit_event:
        emit_event("r2_upload", "started", "Downloading image for R2 upload...")

    data, response_content_type = _download_bytes(image_url, emit_event=emit_event)

    content_type = response_content_type or "image/jpeg"
    ext = mimetypes.guess_extension(content_type) or ".jpg"
    key = f"images/{uuid.uuid4().hex}{ext}"

    client = _get_client()
    bucket = os.environ["R2_BUCKET_NAME"]
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    url = _get_public_url(key)

    if emit_event:
        emit_event("r2_upload", "complete", f"Image uploaded to R2: {url}")

    return {"url": url, "key": key, "demo": False}


def upload_video(video_url, emit_event=None):
    """
    Upload a video to R2 storage.

    If R2 is not configured, returns a demo-mode response with the original URL.
    """
    if not is_configured():
        return {"url": video_url, "key": None, "demo": True}

    if emit_event:
        emit_event("r2_upload", "started", "Downloading video for R2 upload...")

    data, response_content_type = _download_bytes(video_url, emit_event=emit_event)

    content_type = response_content_type or "video/mp4"
    ext = mimetypes.guess_extension(content_type) or ".mp4"
    key = f"videos/{uuid.uuid4().hex}{ext}"

    client = _get_client()
    bucket = os.environ["R2_BUCKET_NAME"]
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    url = _get_public_url(key)

    if emit_event:
        emit_event("r2_upload", "complete", f"Video uploaded to R2: {url}")

    return {"url": url, "key": key, "demo": False}


def upload_bytes(data, content_type="application/octet-stream", folder="files", emit_event=None):
    """
    Upload raw bytes (already in memory) directly to R2.

    Used by providers that return image data inline (e.g. OpenAI gpt-image-1),
    bypassing any upstream temporary CDN.
    """
    if not is_configured():
        return {"url": None, "key": None, "demo": True}

    ext = mimetypes.guess_extension(content_type) or ""
    key = f"{folder}/{uuid.uuid4().hex}{ext}"

    client = _get_client()
    bucket = os.environ["R2_BUCKET_NAME"]
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    url = _get_public_url(key)

    if emit_event:
        emit_event("r2_upload", "complete", f"Bytes uploaded to R2: {url}")

    return {"url": url, "key": key, "demo": False}


def upload_headshot(file_data, filename, emit_event=None):
    """
    Upload a headshot image to R2 storage from raw bytes.

    If R2 is not configured, returns a demo-mode response.
    """
    if not is_configured():
        return {"url": None, "key": None, "demo": True}

    if emit_event:
        emit_event("r2_upload", {"status": "uploading", "type": "headshot"})

    content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
    ext = mimetypes.guess_extension(content_type) or ".jpg"
    key = f"headshots/{uuid.uuid4().hex}{ext}"

    client = _get_client()
    bucket = os.environ["R2_BUCKET_NAME"]
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_data,
        ContentType=content_type,
    )

    url = _get_public_url(key)

    if emit_event:
        emit_event("r2_upload", {"status": "complete", "type": "headshot", "url": url})

    return {"url": url, "key": key, "demo": False}


def get_presigned_url(key, expires_in=604800):
    """Generate a presigned URL for an R2 object (default 7 days)."""
    client = _get_client()
    bucket = os.environ["R2_BUCKET_NAME"]
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def test_connection():
    """Test R2 connectivity by listing up to 1 object."""
    client = _get_client()
    bucket = os.environ["R2_BUCKET_NAME"]
    result = client.list_objects_v2(Bucket=bucket, MaxKeys=1)
    return {"success": True, "bucket": bucket, "objects": result.get("KeyCount", 0)}
