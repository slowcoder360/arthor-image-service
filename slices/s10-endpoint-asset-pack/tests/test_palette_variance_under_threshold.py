"""s10 AC-10: palette close to StyleProfile palette → drift_detected is False."""

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


def test_palette_variance_under_threshold_returns_false():
    try:
        from app.quality.palette_variance import check_palette_drift  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-10: check_palette_drift must be importable ({exc})")

    palette_hex = ["#0A4B6F", "#F4A261", "#FFFFFF"]
    rgb_close_to_primary = (10, 75, 111)
    img_bytes = _make_solid_png(rgb_close_to_primary)
    drift_detected, extracted = check_palette_drift(
        img_bytes, palette_hex, threshold=25.0
    )
    assert drift_detected is False, (
        "AC-10: image very close to a palette color must NOT trigger drift at threshold=25.0"
    )
    assert isinstance(extracted, list) and all(
        isinstance(h, str) and h.startswith("#") for h in extracted
    ), "AC-10: extracted palette must be a list of hex strings"
