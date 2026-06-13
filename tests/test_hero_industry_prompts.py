"""Industry-specific hero prompt guards (cohort review regressions)."""

from __future__ import annotations

import pytest

from app.payload.hero_models import HeroCandidatesRequest, hero_request_to_payload_v1
from app.style.hero_archetypes import resolve_industry
from app.style.hero_prompt_compiler import compile_hero_triad_prompts
from app.style.hero_visual_strategy import resolve_scene_archetype
from app.style.resolver import resolve_style_profile
from tests.test_hero_candidates import _build_hero_request


def _req_for_industry(industry: str) -> HeroCandidatesRequest:
    raw = _build_hero_request()
    raw["business"]["industry"] = industry
    raw["business"]["icp_summary"] = "local families seeking service"
    return HeroCandidatesRequest.model_validate(raw)


@pytest.mark.asyncio
async def test_home_services_prompt_excludes_couch_leisure():
    req = _req_for_industry("hvac repair")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "technician" in text
    assert "couch" in text or "sofa" in text or "leisure" in text
    assert resolve_scene_archetype(req, req.variants[1]) == "desk_side_guidance"


@pytest.mark.asyncio
async def test_healthcare_prompt_excludes_gym_aesthetic():
    req = _req_for_industry("physical therapy clinic")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "gym" in text or "athletic" in text
    assert "clinic" in text or "therapy" in text
    assert resolve_industry("physical therapy clinic").label == "healthcare"


@pytest.mark.asyncio
async def test_legal_story_uses_desk_not_threshold_family():
    req = _req_for_industry("personal injury law")
    assert resolve_scene_archetype(req, req.variants[1]) == "desk_side_guidance"
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[1].prompt.lower()
    assert "desk" in text or "table" in text
    assert "family group" in text or "doorway" in text or "residential" in text


@pytest.mark.asyncio
async def test_landscaping_resolves_outdoor_services():
    req = _req_for_industry("landscaping")
    assert resolve_industry("landscaping").label == "outdoor_services"
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "outdoor" in text or "yard" in text or "lawn" in text
    assert "kitchen" in text or "couch" in text or "interior" in text
