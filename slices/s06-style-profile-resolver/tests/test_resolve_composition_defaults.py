"""s06 AC-4: empty composition_rules → DEFAULT_COMPOSITION."""

from __future__ import annotations

import pytest

from _payload_helpers import base_payload_dict, import_payload_v1


@pytest.mark.asyncio
async def test_default_composition_when_hint_empty():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.defaults import DEFAULT_COMPOSITION  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: defaults + resolver must be importable ({exc})")

    raw = base_payload_dict()
    raw["style_profile_hint"]["composition_rules"] = []
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    expected = list(DEFAULT_COMPOSITION)
    assert list(profile.composition) == expected, (
        f"AC-4: empty composition_rules must yield DEFAULT_COMPOSITION; got {profile.composition!r}"
    )


@pytest.mark.asyncio
async def test_non_empty_hint_overrides_default():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: resolver must be importable ({exc})")

    raw = base_payload_dict()
    raw["style_profile_hint"]["composition_rules"] = ["leading lines", "low horizon"]
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)
    assert "leading lines" in profile.composition, (
        "AC-4: non-empty composition_rules must be honored verbatim"
    )
    assert "low horizon" in profile.composition, (
        "AC-4: non-empty composition_rules must be honored verbatim"
    )
