"""s06 AC-7 / AC-8: build_slot_prompt produces the ADR-0009 §4 template + sha256 hash."""

from __future__ import annotations

import hashlib

import pytest

from _payload_helpers import base_payload_dict, import_payload_v1


@pytest.mark.asyncio
async def test_build_slot_prompt_returns_text_hash_and_template_version():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.prompts import build_slot_prompt  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-7: prompts + resolver must be importable ({exc})")

    payload = PayloadV1.model_validate(base_payload_dict())
    profile = await resolve_style_profile(payload)
    slot = payload.slots[0]
    prompt = build_slot_prompt(profile, slot)

    text = prompt.text
    assert isinstance(text, str) and len(text) > 0, (
        "AC-7: SlotPrompt.text must be a non-empty string"
    )
    assert prompt.prompt_template_version == "1.0", (
        "AC-7/AC-8: SlotPrompt.prompt_template_version must equal '1.0'"
    )
    expected_hash = hashlib.sha256(text.encode()).hexdigest()
    assert prompt.prompt_hash == expected_hash, (
        "AC-7: prompt_hash must equal sha256(text.encode()).hexdigest()"
    )


@pytest.mark.asyncio
async def test_build_slot_prompt_template_includes_lighting_register_avoid():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.prompts import build_slot_prompt  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-7: prompts + resolver must be importable ({exc})")

    payload = PayloadV1.model_validate(base_payload_dict())
    profile = await resolve_style_profile(payload)
    slot = payload.slots[0]
    prompt = build_slot_prompt(profile, slot)
    text_lower = prompt.text.lower()
    assert "lighting" in text_lower, (
        "AC-7: prompt template must include 'Lighting:' line per ADR-0009 §4"
    )
    assert "avoid" in text_lower, (
        "AC-7: prompt template must include 'Avoid:' line per ADR-0009 §4"
    )
    assert profile.register in prompt.text, (
        f"AC-7: prompt template must surface profile.register ({profile.register!r})"
    )
