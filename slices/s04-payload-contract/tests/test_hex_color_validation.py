"""s04 AC-2: hex color validator accepts upper/lower 6-hex; rejects missing # or non-hex."""

from __future__ import annotations

import pytest

from _payload_fixtures import mvp_payload


def _build_with_primary(value: str) -> dict:
    raw = mvp_payload()
    raw["brand_visual"]["palette"]["light"]["primary"] = value
    return raw


def _import_payload_v1():
    try:
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: PayloadV1 must be importable ({exc})")
    return PayloadV1


@pytest.mark.parametrize("value", ["#0A4B6F", "#0a4b6f", "#FFFFFF", "#000000"])
def test_hex_color_accepts_well_formed(value):
    PayloadV1 = _import_payload_v1()
    PayloadV1.model_validate(_build_with_primary(value))


@pytest.mark.parametrize("value", ["0A4B6F", "#GGG", "#0A4B6", "#0A4B6FF", "blue", ""])
def test_hex_color_rejects_malformed(value):
    PayloadV1 = _import_payload_v1()
    try:
        from pydantic import ValidationError
    except ImportError as exc:
        pytest.fail(f"pydantic not installed: {exc}")
    with pytest.raises(ValidationError):
        PayloadV1.model_validate(_build_with_primary(value))
