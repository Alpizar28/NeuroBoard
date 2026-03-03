"""Tests for AudioService.

Covers:
- calculate_hash stability and uniqueness
- preprocess_audio delegates to ffmpeg (mocked so no ffmpeg binary needed)
- transcribe delegates to Whisper (mocked)
- transcribe propagates RuntimeError when faster-whisper is missing
- WHISPER_FALLBACK_TO_API=True swallows RuntimeError and returns empty string
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.services.audio_service import AudioService


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _run(coro):
    """Run an async coroutine synchronously in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ─────────────────────────────────────────────────────────────────────────────
# Hash tests (synchronous — no I/O)
# ─────────────────────────────────────────────────────────────────────────────

def test_calculate_hash_is_stable() -> None:
    data = b"audio content"
    assert AudioService.calculate_hash(data) == AudioService.calculate_hash(data)


def test_calculate_hash_differs_for_different_inputs() -> None:
    assert AudioService.calculate_hash(b"aaa") != AudioService.calculate_hash(b"bbb")


def test_calculate_hash_is_64_hex_chars() -> None:
    result = AudioService.calculate_hash(b"test audio")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


# ─────────────────────────────────────────────────────────────────────────────
# preprocess_audio — mock ffmpeg so no binary is required
# ─────────────────────────────────────────────────────────────────────────────

def test_preprocess_audio_returns_wav_bytes() -> None:
    fake_wav = b"RIFF\x00\x00\x00\x00WAVEfmt "

    with patch(
        "app.services.audio_service._ffmpeg_convert_to_wav",
        return_value=fake_wav,
    ):
        result = _run(AudioService.preprocess_audio(b"raw ogg bytes"))

    assert result == fake_wav


def test_preprocess_audio_propagates_runtime_error() -> None:
    with patch(
        "app.services.audio_service._ffmpeg_convert_to_wav",
        side_effect=RuntimeError("ffmpeg not found"),
    ):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            _run(AudioService.preprocess_audio(b"raw bytes"))


# ─────────────────────────────────────────────────────────────────────────────
# transcribe — mock Whisper so no model download is required
# ─────────────────────────────────────────────────────────────────────────────

def test_transcribe_returns_transcript() -> None:
    with patch(
        "app.services.audio_service._whisper_transcribe",
        return_value="lavar ropa mañana",
    ):
        result = _run(AudioService.transcribe(b"fake wav bytes"))

    assert result == "lavar ropa mañana"


def test_transcribe_returns_empty_string_on_silence() -> None:
    with patch(
        "app.services.audio_service._whisper_transcribe",
        return_value="",
    ):
        result = _run(AudioService.transcribe(b"silence"))

    assert result == ""


def test_transcribe_propagates_error_when_fallback_disabled() -> None:
    from app.core.config import settings

    original = settings.WHISPER_FALLBACK_TO_API
    settings.WHISPER_FALLBACK_TO_API = False
    try:
        with patch(
            "app.services.audio_service._whisper_transcribe",
            side_effect=RuntimeError("model error"),
        ):
            with pytest.raises(RuntimeError, match="model error"):
                _run(AudioService.transcribe(b"bad bytes"))
    finally:
        settings.WHISPER_FALLBACK_TO_API = original


def test_transcribe_returns_empty_when_fallback_enabled() -> None:
    from app.core.config import settings

    original = settings.WHISPER_FALLBACK_TO_API
    settings.WHISPER_FALLBACK_TO_API = True
    try:
        with patch(
            "app.services.audio_service._whisper_transcribe",
            side_effect=RuntimeError("model error"),
        ):
            result = _run(AudioService.transcribe(b"bad bytes"))
            assert result == ""
    finally:
        settings.WHISPER_FALLBACK_TO_API = original


# ─────────────────────────────────────────────────────────────────────────────
# _whisper_transcribe — ImportError when faster-whisper is absent
# ─────────────────────────────────────────────────────────────────────────────

def test_whisper_transcribe_raises_when_package_missing() -> None:
    import builtins
    import sys

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("No module named 'faster_whisper'")
        return original_import(name, *args, **kwargs)

    # Remove any cached model so _whisper_transcribe tries to import fresh
    import app.services.audio_service as audio_mod
    audio_mod._whisper_model_cache.clear()

    with patch("builtins.__import__", side_effect=mock_import):
        from app.services.audio_service import _whisper_transcribe
        with pytest.raises(RuntimeError, match="faster-whisper is not installed"):
            _whisper_transcribe(b"some wav bytes")
