"""s12 AC-5: the probe slot is constructed deterministically — same payload
input produces the same resolved prompt hash.
"""

from __future__ import annotations

import pytest

from _s12_helpers import build_payload


@pytest.mark.asyncio
async def test_probe_slot_is_canonical_for_same_payload():
    try:
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.routes.style_preview import build_probe_slot  # type: ignore[import-not-found]
        from app.style.prompt_builder import build_slot_prompt  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-5: build_probe_slot + build_slot_prompt + resolve_style_profile "
            f"must be importable ({exc})"
        )

    raw = build_payload()
    payload_a = PayloadV1.model_validate(raw)
    payload_b = PayloadV1.model_validate(raw)
    profile_a = await resolve_style_profile(payload_a)
    profile_b = await resolve_style_profile(payload_b)

    probe_a = build_probe_slot(payload_a)
    probe_b = build_probe_slot(payload_b)

    prompt_a = build_slot_prompt(slot=probe_a, style_profile=profile_a, payload=payload_a)
    prompt_b = build_slot_prompt(slot=probe_b, style_profile=profile_b, payload=payload_b)

    assert prompt_a == prompt_b, (
        "AC-5: probe slot must produce identical resolved prompt text for identical payloads"
    )
    assert "professional-services" in prompt_a.lower() or "austin" in prompt_a.lower(), (
        f"AC-5: probe prompt must reference the documented business industry or location; "
        f"got {prompt_a!r}"
    )
