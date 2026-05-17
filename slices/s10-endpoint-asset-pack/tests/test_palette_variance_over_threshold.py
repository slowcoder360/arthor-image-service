"""s10 AC-10: palette very different from StyleProfile → drift_detected is True; metadata patched."""

from __future__ import annotations

import io

import pytest


def _make_solid_png(rgb: tuple[int, int, int]) -> bytes:
    try:
        from PIL import Image
    except ImportError as exc:
        pytest.fail(f"Pillow not installed: {exc}")
    img = Image.new("RGB", (64, 64), color=rgb)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_palette_variance_over_threshold_returns_true():
    try:
        from app.quality.palette_variance import check_palette_drift  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-10: check_palette_drift must be importable ({exc})")

    palette_hex = ["#0A4B6F", "#F4A261", "#FFFFFF"]
    rgb_far_from_palette = (255, 0, 255)
    img_bytes = _make_solid_png(rgb_far_from_palette)
    drift_detected, extracted = check_palette_drift(
        img_bytes, palette_hex, threshold=25.0
    )
    assert drift_detected is True, (
        "AC-10: vivid magenta vs blue/orange palette must trigger drift at threshold=25.0"
    )
    assert extracted, (
        "AC-10: extracted palette must be a non-empty list of hex strings on drift"
    )
