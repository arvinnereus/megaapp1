"""Unit tests for services.r2_storage."""
from unittest.mock import patch, MagicMock

import pytest
import requests

from services import r2_storage


def test_download_bytes_succeeds_on_first_try():
    """Normal path: no SSL error, no retry."""
    fake = MagicMock(content=b"abc", headers={"Content-Type": "image/png"})
    fake.raise_for_status = MagicMock()
    with patch("services.r2_storage.requests.get", return_value=fake) as mock_get:
        data, ct = r2_storage._download_bytes("https://example.com/x.png")
    assert data == b"abc"
    assert ct == "image/png"
    assert mock_get.call_count == 1
    # verify default behaviour: no `verify=False` passed
    assert mock_get.call_args.kwargs.get("verify") is not False


def test_download_bytes_retries_with_verify_false_on_ssl_error():
    """SSLError on first call → retry once with verify=False → return bytes."""
    fake = MagicMock(content=b"jpegbytes", headers={"Content-Type": "image/jpeg"})
    fake.raise_for_status = MagicMock()

    call_results = [requests.exceptions.SSLError("BAD_SIGNATURE"), fake]

    def side_effect(*args, **kwargs):
        result = call_results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    with patch("services.r2_storage.requests.get", side_effect=side_effect) as mock_get:
        data, ct = r2_storage._download_bytes("https://flaky-cdn.example/img.jpg")

    assert data == b"jpegbytes"
    assert ct == "image/jpeg"
    assert mock_get.call_count == 2
    # the retry must pass verify=False
    assert mock_get.call_args_list[1].kwargs.get("verify") is False


def test_download_bytes_propagates_ssl_error_if_retry_also_fails():
    """Both attempts fail → exception bubbles up so the caller can log it."""
    with patch("services.r2_storage.requests.get",
               side_effect=requests.exceptions.SSLError("BAD_SIGNATURE")):
        with pytest.raises(requests.exceptions.SSLError):
            r2_storage._download_bytes("https://broken.example/x.jpg")


def test_upload_image_passthrough_when_r2_not_configured(monkeypatch):
    """Without R2 env vars, upload_image returns the original URL in demo mode."""
    for v in r2_storage.R2_ENV_VARS:
        monkeypatch.delenv(v, raising=False)
    result = r2_storage.upload_image("https://cdn.example/img.png")
    assert result == {"url": "https://cdn.example/img.png", "key": None, "demo": True}
