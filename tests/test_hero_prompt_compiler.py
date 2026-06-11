"""Deterministic hero prompt compiler tests."""

from __future__ import annotations

import uuid

import pytest

from app.payload.hero_models import HeroCandidatesRequest
from app.style.hero_prompt_compiler import (
    compile_hero_triad_prompts,
    compile_variant_prompt,
    prompt_text_hash,
)
from app.style.resolver import resolve_style_profile
from tests.test_hero_candidates import _build_hero_request


@pytest.mark.asyncio
async def test_compile_dental_hero_job_trust_not_equipment():
    raw = _build_hero_request()
    req = HeroCandidatesRequest.model_validate(raw)
    from app.payload.hero_models import hero_request_to_payload_v1

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    prompts = compile_hero_triad_prompts(req, profile)
    assert len(prompts) == 3
    search = prompts[0].prompt
    assert prompts[0].compiler_version == "3.0"
    assert prompts[0].industry_label == "dental"
    assert prompts[0].hero_job == "trust"
    assert prompts[0].scene_archetype == "shared_joy"
    assert prompts[1].scene_archetype == "shared_joy"
    assert prompts[2].scene_archetype == "confident_smile"
    assert "Scene archetype: shared_joy" in search
    assert "candid shared joy" in search.lower()
    assert "consultation" not in search.lower()
    body, _, _ = search.partition("Avoid:")
    assert "no operatory" in body.lower()
    assert "no dental chair" in body.lower()
    assert "visual anchors" not in search.lower()
    assert "dental operatory or welcoming" not in search.lower()
    assert "blank left half" in search.lower() or "blank void" in search.lower()
    assert "#0A4B6F" in search
    assert "never render text" in search.lower()
    assert "Find a dentist" not in search
    assert prompts[0].prompt_hash == prompt_text_hash(search)


@pytest.mark.asyncio
async def test_compile_is_stable_for_same_input():
    raw = _build_hero_request(idem_key=f"hero-compile-{uuid.uuid4()}")
    req = HeroCandidatesRequest.model_validate(raw)
    from app.payload.hero_models import hero_request_to_payload_v1

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    a = compile_hero_triad_prompts(req, profile)
    b = compile_hero_triad_prompts(req, profile)
    assert [x.prompt_hash for x in a] == [x.prompt_hash for x in b]


@pytest.mark.asyncio
async def test_tone_variants_differ():
    raw = _build_hero_request(idem_key=f"hero-tone-{uuid.uuid4()}")
    req = HeroCandidatesRequest.model_validate(raw)
    from app.payload.hero_models import hero_request_to_payload_v1

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    prompts = compile_hero_triad_prompts(req, profile)
    hashes = {p.tone_angle: p.prompt_hash for p in prompts}
    assert len(set(hashes.values())) == 3


@pytest.mark.asyncio
async def test_mobile_viewport_portrait_composition():
    raw = _build_hero_request()
    raw["hero_viewport"] = "mobile"
    req = HeroCandidatesRequest.model_validate(raw)
    from app.payload.hero_models import hero_request_to_payload_v1, variant_to_slot

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    prompts = compile_hero_triad_prompts(req, profile)
    slot = variant_to_slot(req, req.variants[0], 0)
    assert slot.layout.dimensions.w == 1024
    assert slot.layout.dimensions.h == 1536
    assert prompts[0].hero_viewport == "mobile"
    text = prompts[0].prompt
    assert "1024x1536" in text
    assert "portrait" in text.lower() or "mobile" in text.lower()
    assert "upper" in text.lower() or "quiet" in text.lower()

    raw = _build_hero_request()
    raw["business"]["industry"] = "personal injury law"
    req = HeroCandidatesRequest.model_validate(raw)
    from app.payload.hero_models import hero_request_to_payload_v1

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_variant_prompt(req, req.variants[0], 0, profile)
    assert "Scene archetype" in text
    assert "law office" in text.lower() or "legal" in text.lower() or "professional" in text.lower()
    assert "empty conference room" in text.lower()
