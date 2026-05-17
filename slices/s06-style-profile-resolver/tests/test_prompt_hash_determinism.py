"""s06 AC-9: identical inputs produce identical prompt text + hash; one-char change shifts hash."""

from __future__ import annotations

import pytest

from _payload_helpers import base_payload_dict, import_payload_v1


@pytest.mark.asyncio
async def test_identical_inputs_produce_identical_hash():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.prompts import build_slot_prompt  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-9: resolver/prompts must be importable ({exc})")

    raw = base_payload_dict()
    payload_a = PayloadV1.model_validate(raw)
    payload_b = PayloadV1.model_validate(raw)

    profile_a = await resolve_style_profile(payload_a)
    profile_b = await resolve_style_profile(payload_b)

    prompt_a = build_slot_prompt(profile_a, payload_a.slots[0])
    prompt_b = build_slot_prompt(profile_b, payload_b.slots[0])

    assert prompt_a.text == prompt_b.text, (
        "AC-9: identical inputs must produce identical prompt text"
    )


@pytest.mark.asyncio
async def test_changing_subject_primary_changes_hash():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.prompts import build_slot_prompt  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-9: resolver/prompts must be importable ({exc})")

    raw_a = base_payload_dict()
    raw_b = base_payload_dict()
    raw_b["slots"][0]["subject"]["primary"] = "shifted subject"

    payload_a = PayloadV1.model_validate(raw_a)
    payload_b = PayloadV1.model_validate(raw_b)

    profile_a = await resolve_style_profile(payload_a)
    profile_b = await resolve_style_profile(payload_b)

    prompt_a = build_slot_prompt(profile_a, payload_a.slots[0])
    prompt_b = build_slot_prompt(profile_b, payload_b.slots[0])

    assert prompt_a.prompt_hash != prompt_b.prompt_hash, (
        "AC-9: a one-field change must produce a different prompt_hash"
    )
