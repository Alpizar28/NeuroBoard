"""Tests for ImageService.

Covers:
- SHA256 hash stability
- Mode conversion (RGBA, Palette, Grayscale → RGB)
- Resize-down behaviour (never upscale)
- Output is valid JPEG bytes
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.image_service import ImageService


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_image_bytes(width: int = 100, height: int = 100, mode: str = "RGB") -> bytes:
    """Create a minimal in-memory image and return its raw bytes."""
    img = Image.new(mode, (width, height), color=(128, 64, 32) if mode in {"RGB", "RGBA"} else 128)
    buf = io.BytesIO()
    fmt = "PNG"  # PNG supports all modes; we test our service converts the output
    img.save(buf, format=fmt)
    return buf.getvalue()


def _open_result(result_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(result_bytes))


# ─────────────────────────────────────────────────────────────────────────────
# Hash tests
# ─────────────────────────────────────────────────────────────────────────────

def test_calculate_hash_is_stable() -> None:
    data = b"hello world"
    assert ImageService.calculate_hash(data) == ImageService.calculate_hash(data)


def test_calculate_hash_differs_for_different_inputs() -> None:
    assert ImageService.calculate_hash(b"aaa") != ImageService.calculate_hash(b"bbb")


def test_calculate_hash_is_64_hex_chars() -> None:
    result = ImageService.calculate_hash(b"test")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


# ─────────────────────────────────────────────────────────────────────────────
# Preprocessing tests
# ─────────────────────────────────────────────────────────────────────────────

def test_preprocess_returns_jpeg_bytes() -> None:
    result = ImageService.preprocess_image(_make_image_bytes())
    img = _open_result(result)
    assert img.format == "JPEG"


def test_preprocess_outputs_rgb_mode() -> None:
    result = ImageService.preprocess_image(_make_image_bytes())
    img = _open_result(result)
    assert img.mode == "RGB"


def test_preprocess_converts_rgba_to_rgb() -> None:
    rgba_bytes = _make_image_bytes(mode="RGBA")
    result = ImageService.preprocess_image(rgba_bytes)
    img = _open_result(result)
    assert img.mode == "RGB"


def test_preprocess_converts_palette_to_rgb() -> None:
    # Create a palette-mode (P) image
    base = Image.new("RGB", (50, 50), color=(10, 20, 30))
    pal_img = base.quantize()  # converts to P mode
    assert pal_img.mode == "P"
    buf = io.BytesIO()
    pal_img.save(buf, format="PNG")
    result = ImageService.preprocess_image(buf.getvalue())
    img = _open_result(result)
    assert img.mode == "RGB"


def test_preprocess_converts_grayscale_to_rgb() -> None:
    gray_bytes = _make_image_bytes(mode="L")
    result = ImageService.preprocess_image(gray_bytes)
    img = _open_result(result)
    assert img.mode == "RGB"


def test_preprocess_resizes_down_when_over_max_width() -> None:
    wide_bytes = _make_image_bytes(width=2000, height=500)
    result = ImageService.preprocess_image(wide_bytes, max_width=800)
    img = _open_result(result)
    assert img.width == 800
    # Height should be scaled proportionally: 500 * (800/2000) = 200
    assert img.height == 200


def test_preprocess_does_not_upscale_small_image() -> None:
    small_bytes = _make_image_bytes(width=200, height=100)
    result = ImageService.preprocess_image(small_bytes, max_width=1024)
    img = _open_result(result)
    assert img.width == 200  # unchanged — never upscale
    assert img.height == 100
