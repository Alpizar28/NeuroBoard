"""Audio service for NeuroBoard.

Responsibilities:
- Calculate SHA256 hash of raw audio bytes (for deduplication)
- Preprocess audio bytes to mono 16 kHz WAV via ffmpeg (in a thread pool so
  uvicorn's event loop is never blocked)
- Transcribe audio using faster-whisper (local, CPU) with optional fallback to
  an HTTP transcription API

All CPU-bound / blocking work runs inside ``asyncio.get_event_loop().run_in_executor``
so the ASGI worker stays responsive while Whisper loads and runs.
"""
from __future__ import annotations

import asyncio
import io
import logging
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from app.core.config import settings
from app.utils.hashing import sha256_bytes

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Shared thread pool — one thread is sufficient since we run one Whisper model
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="whisper")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (synchronous, run in executor)
# ─────────────────────────────────────────────────────────────────────────────

def _ffmpeg_convert_to_wav(audio_bytes: bytes) -> bytes:
    """Convert arbitrary audio bytes to mono 16 kHz PCM WAV using ffmpeg.

    Raises ``RuntimeError`` if ffmpeg is not installed or conversion fails.
    """
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as src_file:
        src_path = src_file.name
        src_file.write(audio_bytes)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as dst_file:
        dst_path = dst_file.name

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",           # overwrite output
                "-i", src_path,
                "-ar", "16000", # sample rate 16 kHz
                "-ac", "1",     # mono
                "-f", "wav",
                dst_path,
            ],
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg exited with code {result.returncode}: "
                f"{result.stderr.decode(errors='replace')}"
            )
        with open(dst_path, "rb") as f:
            return f.read()
    finally:
        import os
        try:
            os.unlink(src_path)
        except OSError:
            pass
        try:
            os.unlink(dst_path)
        except OSError:
            pass


def _whisper_transcribe(wav_bytes: bytes) -> str:
    """Run faster-whisper on WAV bytes and return the full transcript.

    Loads the model lazily on first call; subsequent calls reuse the cached
    instance (within the same executor thread).
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Add it to requirements.txt."
        ) from exc

    model = _get_whisper_model()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(wav_bytes)

    try:
        segments, _info = model.transcribe(
            tmp_path,
            language=settings.WHISPER_LANGUAGE or None,
            beam_size=5,
        )
        return " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# Module-level cache so the model is loaded only once per process
_whisper_model_cache: dict[str, object] = {}


def _get_whisper_model():
    """Return a cached WhisperModel, loading it on first call."""
    key = f"{settings.WHISPER_MODEL_SIZE}:{settings.WHISPER_DEVICE}"
    if key not in _whisper_model_cache:
        from faster_whisper import WhisperModel  # type: ignore[import]
        logger.info(
            "Loading Whisper model '%s' on device '%s'…",
            settings.WHISPER_MODEL_SIZE,
            settings.WHISPER_DEVICE,
        )
        _whisper_model_cache[key] = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device=settings.WHISPER_DEVICE,
            compute_type="int8",  # most compatible on CPU
        )
        logger.info("Whisper model loaded.")
    return _whisper_model_cache[key]


# ─────────────────────────────────────────────────────────────────────────────
# Public AudioService
# ─────────────────────────────────────────────────────────────────────────────

class AudioService:
    """Stateless service for audio hashing, preprocessing, and transcription."""

    @staticmethod
    def calculate_hash(audio_bytes: bytes) -> str:
        """Return SHA256 hex digest of raw audio bytes for deduplication."""
        return sha256_bytes(audio_bytes)

    @staticmethod
    async def preprocess_audio(audio_bytes: bytes) -> bytes:
        """Convert audio to mono 16 kHz WAV, non-blocking.

        Runs ffmpeg conversion in the shared thread-pool executor so the
        asyncio event loop is never blocked.

        Returns WAV bytes ready for Whisper.
        Raises ``RuntimeError`` if ffmpeg is unavailable or fails.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _ffmpeg_convert_to_wav, audio_bytes)

    @staticmethod
    async def transcribe(wav_bytes: bytes) -> str:
        """Transcribe WAV bytes using faster-whisper, non-blocking.

        Runs inference in the shared thread-pool executor.
        Falls back to an empty string if transcription fails and
        ``WHISPER_FALLBACK_TO_API`` is False (API fallback not yet implemented).

        Returns the transcript as a single string (may be empty).
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(_executor, _whisper_transcribe, wav_bytes)
        except Exception as exc:
            if settings.WHISPER_FALLBACK_TO_API:
                logger.warning(
                    "Whisper local transcription failed (%s); API fallback not yet "
                    "implemented — returning empty transcript.",
                    exc,
                )
                return ""
            raise
