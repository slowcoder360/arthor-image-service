"""Tests for hero pipeline improvement plan (Phase 0–2)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.payload.hero_models import (
    HeroCandidatesRequest,
    build_hero_copy_overlay_metadata,
    hero_request_to_payload_v1,
    variant_to_slot,
)
from app.quality.hero_failure_modes import classify_hero_failure
from app.style.hero_archetypes import safe_area_inset_pct
from app.style.prompt_improver import _improver_applies
from tests.test_hero_candidates import _build_hero_request


def test_offer_tone_safe_area_inset_45():
    raw = _build_hero_request()
    req = HeroCandidatesRequest.model_validate(raw)
    offer_slot = variant_to_slot(req, req.variants[2], 2)
    assert req.variants[2].tone_angle == "offer"
    assert offer_slot.layout.safe_area.inset_pct == 45
    assert safe_area_inset_pct("offer") == 45
    assert safe_area_inset_pct("search") == 40


@pytest.mark.asyncio
async def test_story_prompt_excludes_navigation_wording_and_empty_left_void():
    raw = _build_hero_request()
    req = HeroCandidatesRequest.model_validate(raw)
    from app.style.hero_prompt_compiler import compile_hero_triad_prompts
    from app.style.resolver import resolve_style_profile

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    prompts = compile_hero_triad_prompts(req, profile)
    story = prompts[1].prompt.lower()
    assert "layout intent" not in story
    assert "site header overlay" in story or "header overlay" in story
    assert "blank void" not in story
    assert req.variants[1].headline not in prompts[1].prompt


def test_classify_moderation_blocked():
    assert classify_hero_failure("content_policy_violation: moderation_blocked") == "moderation_blocked"


def test_classify_provider_timeout():
    assert classify_hero_failure("request timed out after 30s") == "provider_timeout"


def test_improver_canary_deterministic():
    assert _improver_applies("hero:test-key", 0.0) is False
    assert _improver_applies("hero:test-key", 100.0) is True


@pytest.mark.asyncio
async def test_hero_candidates_v2_copy_overlay_metadata():
    raw = _build_hero_request()
    raw["payload_version"] = "hero_candidates.2"
    raw["variants"][2]["copy_overlay"] = {
        "primary_cta": "Book now",
        "nav_labels": ["Services", "About"],
    }
    req = HeroCandidatesRequest.model_validate(raw)
    assert req.variants[2].copy_metrics is not None
    assert req.variants[2].copy_metrics.has_cta is True
    assert req.variants[2].copy_metrics.nav_count == 2
    overlay = build_hero_copy_overlay_metadata(req)
    assert overlay[2]["primary_cta"] == "Book now"

    from app.style.hero_prompt_compiler import compile_variant_prompt
    from app.style.resolver import resolve_style_profile

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    prompt = compile_variant_prompt(req, req.variants[2], 2, profile)
    assert "Book now" not in prompt


@pytest.mark.asyncio
async def test_offer_prompt_widens_cta_zone_when_has_cta():
    raw = _build_hero_request()
    raw["variants"][2]["copy_metrics"] = {
        "headline_chars": 20,
        "has_subhead": True,
        "has_cta": True,
        "cta_chars": 8,
        "nav_count": 0,
    }
    req = HeroCandidatesRequest.model_validate(raw)
    from app.style.hero_prompt_compiler import compile_variant_prompt
    from app.style.resolver import resolve_style_profile

    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_variant_prompt(req, req.variants[2], 2, profile)
    assert "lower-left" in text.lower()


def test_settings_model_defaults():
    s = Settings()
    assert s.openai_image_model == "gpt-image-2"
    assert s.hero_default_provider == "openai_image"


def test_google_pro_model_cost_for_hero_size():
    from app.providers.google_nano_banana import GoogleCostTable

    cents = GoogleCostTable.cost_for("gemini-3-pro-image", (1536, 1024))
    assert isinstance(cents, int) and cents > 0
