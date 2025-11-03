import io
import os
import types
import tempfile

import pytest

from app import create_app, validate_instagram_url_or_raise


def test_validate_instagram_url_ok():
    validate_instagram_url_or_raise("https://www.instagram.com/reel/abc123/")


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "not-a-url",
        "https://example.com/reel/x/",
        "https://www.instagram.com/",
    ],
)
def test_validate_instagram_url_bad(bad):
    with pytest.raises(ValueError):
        validate_instagram_url_or_raise(bad)


def test_transcribe_route_happy_path(monkeypatch, tmp_path):
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test")
    client = app.test_client()

    # Mock downloader to return a temp file path
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"fake mp4 data")

from app import download_instagram_video, transcribe_with_whisper_local

    def fake_download(url: str):
        return str(video_path), "video.mp4"

    def fake_transcribe(path: str):
        assert os.path.exists(path)
        return "hello world"

    monkeypatch.setattr("app.download_instagram_video", fake_download)
    monkeypatch.setattr("app.transcribe_with_whisper_local", fake_transcribe)

    resp = client.post(
        "/transcribe", data={"instagram_url": "https://www.instagram.com/reel/abc/"})
    assert resp.status_code == 200
    assert b"Transcri\xc3\xa7\xc3\xa3o" in resp.data
    assert b"hello world" in resp.data
