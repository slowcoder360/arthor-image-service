"""s06 AC-4: palette is copied byte-for-byte from payload.brand_visual.palette."""

from __future__ import annotations

import pytest

from _payload_helpers import base_payload_dict, import_payload_v1


@pytest.mark.asyncio
async def test_palette_is_copied_verbatim_from_payload():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: resolve_style_profile must be importable ({exc})")

    raw = base_payload_dict()
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    expected_primary = raw["brand_visual"]["palette"]["light"]["primary"]
    profile_palette = (
        profile.palette.model_dump()
        if hasattr(profile.palette, "model_dump")
        else dict(profile.palette)
    )
    actual_primary = profile_palette["light"]["primary"]
    assert actual_primary == expected_primary, (
        f"AC-4: palette.light.primary must equal payload value {expected_primary!r}; got {actual_primary!r}"
    )
