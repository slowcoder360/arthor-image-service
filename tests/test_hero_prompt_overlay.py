"""Hero-candidates prompts reserve overlay zones; copy is not rendered."""

from __future__ import annotations

import uuid

import pytest

from app.payload.hero_models import HeroCandidatesRequest, hero_request_to_payload_v1
from app.style.prompts import build_slot_prompt
from app.style.resolver import resolve_style_profile
from tests.test_hero_candidates import _build_hero_request


@pytest.mark.asyncio
async def test_hero_prompt_uses_copy_for_placement_not_rendering():
    raw = _build_hero_request(idem_key=f"hero-prompt-{uuid.uuid4()}")
    headline = raw["variants"][0]["headline"]
    req = HeroCandidatesRequest.model_validate(raw)
    payload = hero_request_to_payload_v1(req)
    profile = await resolve_style_profile(payload)
    slot = payload.slots[0]
    prompt = build_slot_prompt(profile, slot)

    assert "DO NOT render as text" in prompt.text
    assert headline in prompt.text
    assert "top 14%" in prompt.text
    assert "left 40%" in prompt.text
    assert "background plate only" in prompt.text
