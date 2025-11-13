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

# Limites de recursos para ambiente de produção
MAX_VIDEO_DURATION = 180  # 3 minutos
MAX_VIDEO_SIZE_MB = 50  # Reduzido de 200MB para 50MB


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get(
        "FLASK_SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = MAX_VIDEO_SIZE_MB * 1024 * 1024

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html", transcript=None, error=None)

    @app.route("/transcribe", methods=["POST"])
    def transcribe():
        input_url = (request.form.get("instagram_url") or "").strip()

        if not input_url:
            flash("Informe uma URL do Instagram.", "error")
            return redirect(url_for("index"))

        try:
            validate_instagram_url_or_raise(input_url)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))

        file_path = None
        wav_path = None

        try:
            file_path = download_instagram_audio_only(input_url)

            # Validar duração do vídeo
            duration = get_audio_duration(file_path)
            if duration > MAX_VIDEO_DURATION:
                raise ValueError(
                    f"Vídeo muito longo ({int(duration)}s). Máximo: {MAX_VIDEO_DURATION}s"
                )

            # Transcrever
            transcript_text = transcribe_with_whisper_local(file_path)

            flash("Transcrição concluída com sucesso!", "success")
            return render_template("index.html", transcript=transcript_text, error=None)

        except Exception as exc:
            error_msg = str(exc)

            if "rate-limit" in error_msg.lower() or "login required" in error_msg.lower():
                error_msg = (
                    "Instagram bloqueou a requisição. "
                    "Tente novamente em alguns minutos ou use uma URL diferente."
                )

            flash(f"Erro: {error_msg}", "error")
            return redirect(url_for("index"))

        finally:
            # Limpeza garantida de arquivos temporários
            cleanup_files([file_path, wav_path])

    return app


def validate_instagram_url_or_raise(url: str) -> None:
    if not url:
        raise ValueError("Informe uma URL do Instagram.")

    pattern = re.compile(r"^https?://([^/]+)(/.*)?$", re.IGNORECASE)
    match = pattern.match(url)
    if not match:
        raise ValueError("URL inválida.")

    host = match.group(1).lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError("A URL deve ser do domínio instagram.com.")

        raise ValueError(
            "Forneça a URL de um post, reel ou vídeo do Instagram."
        )


def download_instagram_audio_only(url: str) -> str:
    """
    Download apenas o áudio do Instagram.
    Implementa estratégias contra rate-limit.
    """
    temp_dir = tempfile.mkdtemp(prefix="insta_audio_")
    unique = uuid.uuid4().hex[:8]

    output_path = os.path.join(temp_dir, f"audio_{unique}.m4a")

    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestaudio/best",  # Apenas áudio
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,

        # ANTI-RATE-LIMIT: User-Agent moderno
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
            "Referer": "https://www.instagram.com/",
        },

        # Cookies (se disponível no ambiente)
        "cookiesfrombrowser": None,  # Desabilitado por padrão

        # Limites
        "max_filesize": MAX_VIDEO_SIZE_MB * 1024 * 1024,
        "ratelimit": 3_000_000,  # 3MB/s (mais conservador)

        # Extrair sem pós-processamento
        "postprocessors": [],
        "extract_flat": False,
    }

    # Se tiver cookies em variável de ambiente (solução pro rate-limit)
    cookies_path = os.environ.get("INSTAGRAM_COOKIES_PATH")
    if cookies_path and os.path.exists(cookies_path):
        ydl_opts["cookiefile"] = cookies_path

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Buscar arquivo baixado
            downloaded_file = find_downloaded_file(temp_dir)
            if not downloaded_file:
                raise RuntimeError("Arquivo não foi baixado corretamente.")

            return downloaded_file

    except Exception as e:
        # Limpar diretório temporário em caso de erro
        cleanup_files([temp_dir])
        raise


def find_downloaded_file(directory: str) -> Optional[str]:
    """Localiza o arquivo de áudio baixado."""
    for filename in os.listdir(directory):
        if filename.endswith(('.m4a', '.mp3', '.opus', '.webm', '.mp4')):
            return os.path.join(directory, filename)
    return None


def get_audio_duration(file_path: str) -> float:
    """Obtém duração do áudio em segundos usando ffprobe."""
    ffprobe = imageio_ffmpeg.get_ffmpeg_exe().replace('ffmpeg', 'ffprobe')

    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def extract_wav_with_bundled_ffmpeg(input_file_path: str) -> str:
    """Extrai WAV 16kHz mono usando ffmpeg empacotado."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    wav_path = os.path.splitext(input_file_path)[0] + "_audio.wav"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", input_file_path,
        "-vn",  # Sem vídeo
        "-ac", "1",  # Mono
        "-ar", "16000",  # 16kHz
        "-f", "wav",
        wav_path,
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60  # Timeout de 1 minuto
    )

    if proc.returncode != 0 or not os.path.exists(wav_path):
        raise RuntimeError(f"Falha ao extrair áudio: {proc.stderr.decode()}")

    return wav_path


def transcribe_with_whisper_local(file_path: str) -> str:
    """
    Transcreve áudio usando Whisper otimizado para produção.
    """
    wav_path = None

    try:
        # Extrair WAV
        wav_path = extract_wav_with_bundled_ffmpeg(file_path)

        # OTIMIZAÇÃO: Usar modelo menor em produção
        is_production = os.environ.get("FLASK_ENV") == "production"
        model_size = "tiny" if is_production else os.environ.get(
            "WHISPER_MODEL", "base")

        # Carregar modelo com configurações leves
        model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",  # Quantização para economia de memória
            num_workers=1,  # Reduzir threads
        )

        # Transcrever com beam_size mínimo
        segments, info = model.transcribe(
            wav_path,
            beam_size=1,  # Mínimo para velocidade
            language="pt",  # Forçar português (economiza detecção)
            vad_filter=True,  # Filtrar silêncios
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Coletar texto
        text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]

        return " ".join(text_parts) if text_parts else "Nenhuma fala detectada."

    finally:
        cleanup_files([wav_path])


def cleanup_files(paths: list) -> None:
    """Remove arquivos/diretórios temporários com segurança."""
    for path in paths:
        if not path or not isinstance(path, str):
            continue

        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                import shutil
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
