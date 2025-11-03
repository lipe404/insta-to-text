import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from typing import Optional, Tuple

from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel
import subprocess
import imageio_ffmpeg


ALLOWED_HOSTS = {
    "instagram.com",
    "www.instagram.com",
    "instagram.cdninstagram.com",
    "cdninstagram.com",
}


def create_app() -> Flask:
    app = Flask(__name__)
    # Use a stable default SECRET_KEY if none provided (avoids session errors)
    app.config["SECRET_KEY"] = os.environ.get(
        "FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB safety

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html", transcript=None, error=None)

    @app.route("/transcribe", methods=["POST"])
    def transcribe():
        input_url = (request.form.get("instagram_url") or "").strip()
        try:
            validate_instagram_url_or_raise(input_url)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))

        # Download video as MP4 without local ffmpeg postprocessing
        try:
            file_path, filename = download_instagram_video(input_url)
        except Exception as exc:  # noqa: BLE001
            flash(f"Falha ao baixar o vídeo: {exc}", "error")
            return redirect(url_for("index"))

        try:
            transcript_text = transcribe_with_whisper_local(file_path)
        except Exception as exc:  # noqa: BLE001
            flash(f"Falha na transcrição: {exc}", "error")
            transcript_text = None
        finally:
            # Always cleanup downloaded file
            try:
                os.remove(file_path)
            except OSError:
                pass

        return render_template("index.html", transcript=transcript_text, error=None)

    return app


def validate_instagram_url_or_raise(url: str) -> None:
    if not url:
        raise ValueError("Informe uma URL do Instagram.")
    # Basic structure and host allowlist (mitigate SSRF)
    pattern = re.compile(r"^https?://([^/]+)(/.*)?$", re.IGNORECASE)
    match = pattern.match(url)
    if not match:
        raise ValueError("URL inválida.")
    host = match.group(1).lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError("A URL deve ser do domínio instagram.com.")
    # Optional: restrict to common Instagram paths
    if not re.search(r"/(reel|reels|p|tv)/", url, flags=re.IGNORECASE):
        raise ValueError(
            "Forneça a URL de um post, reel ou vídeo do Instagram.")


@contextmanager
def temp_download_dir() -> Tuple[str, str]:
    base_tmp = tempfile.gettempdir()
    session_dir = os.path.join(base_tmp, f"insta_to_text_{uuid.uuid4().hex}")
    os.makedirs(session_dir, exist_ok=True)
    try:
        yield session_dir, base_tmp
    finally:
        try:
            os.rmdir(session_dir)
        except OSError:
            # Directory may not be empty if removal failed earlier; ignore
            pass


def download_instagram_video(url: str) -> Tuple[str, str]:
    """Download Instagram media as a single MP4 file using yt-dlp.

    Returns (file_path, filename).
    """
    with temp_download_dir() as (session_dir, _):
        # Choose a format that results in a single container file without postproc
        # Prefer MP4 if available; fall back to best single file
        format_selector = "best[ext=mp4]/best"
        unique = uuid.uuid4().hex
        # Use a safe template; yt-dlp will append extension
        outtmpl = os.path.join(session_dir, f"%(title).80s-{unique}.%(ext)s")
        ydl_opts = {
            "outtmpl": outtmpl,
            "format": format_selector,
            "restrictfilenames": True,
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 2,
            "ratelimit": 5_000_000,  # ~5MB/s to be gentle
            "trim_filenames": 120,
            "max_filesize": 200 * 1024 * 1024,  # 200 MB max
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Compute resulting path
            ext = info.get("ext") or "mp4"
            title = info.get("title") or f"instagram-{unique}"
            safe_name = secure_filename(f"{title}-{unique}.{ext}")
            # yt-dlp used template already; search for the downloaded file in dir
            # If multiple files match, pick the largest
            candidates = [
                os.path.join(session_dir, f)
                for f in os.listdir(session_dir)
                if f.endswith(f".{ext}")
            ]
            if not candidates:
                raise RuntimeError(
                    "Não foi possível localizar o arquivo baixado.")
            candidates.sort(key=lambda p: os.path.getsize(p), reverse=True)
            file_path = candidates[0]
            return file_path, safe_name


def extract_wav_with_bundled_ffmpeg(input_video_path: str) -> str:
    """Extract 16kHz mono WAV using a bundled static ffmpeg binary (no system install)."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    wav_path = os.path.splitext(input_video_path)[0] + "_audio.wav"
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", input_video_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-f", "wav",
        wav_path,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0 or not os.path.exists(wav_path):
        raise RuntimeError("Falha ao extrair áudio com ffmpeg empacotado.")
    return wav_path


def transcribe_with_whisper_local(file_path: str) -> str:
    # Convert input MP4 to WAV using bundled ffmpeg to ensure decoding works without system ffmpeg
    wav_path = extract_wav_with_bundled_ffmpeg(file_path)
    try:
        # Use a small model for speed; change to "base"/"small" as desired
        model_size = os.environ.get("WHISPER_MODEL", "small")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, info = model.transcribe(wav_path, beam_size=1, language=None)
        text_parts = []
        for seg in segments:
            text_parts.append(seg.text)
        return " ".join(part.strip() for part in text_parts if part.strip())
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(
        os.environ.get("PORT", "8000")), debug=True)
