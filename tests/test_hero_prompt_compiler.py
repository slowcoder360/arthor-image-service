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
async def test_compile_dental_includes_industry_anchors_and_palette():
    raw = _build_hero_request()
    req = HeroCandidatesRequest.model_validate(raw)
    from app.payload.hero_models import hero_request_to_payload_v1

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    prompts = compile_hero_triad_prompts(req, profile)
    assert len(prompts) == 3
    search = prompts[0].prompt
    assert prompts[0].industry_label == "dental"
    assert "dental operatory" in search or "dental chair" in search
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
async def test_legal_industry_archetype():
    raw = _build_hero_request()
    raw["business"]["industry"] = "personal injury law"
    req = HeroCandidatesRequest.model_validate(raw)
    from app.payload.hero_models import hero_request_to_payload_v1

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_variant_prompt(req, req.variants[0], 0, profile)
    assert "law office" in text.lower()
    assert "courtroom" in text.lower() or "gavel" in text.lower()
