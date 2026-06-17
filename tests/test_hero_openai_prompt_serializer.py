"""Tests for gpt-image-2 hero prompt serializer."""

from __future__ import annotations

import pytest

from app.style.hero_openai_prompt_serializer import (
    HeroPromptBrief,
    composition_block,
    serialize_openai_hero_prompt,
)


def test_serialize_uses_model_native_sections_not_debug_labels():
    brief = HeroPromptBrief(
        brand_context="Acme Dental (dental, Austin, TX)",
        subject="candid shared joy — two people in warm eye contact",
        people="parent and child; natural smiles",
        setting="bright modern dental clinic reception area",
        composition=composition_block(tone_angle="search", inset_pct=40, is_mobile=False, has_cta=False),
        photography="Photorealistic quality. 50mm lens. Lighting: soft window light.",
        mood_and_color="calm, family-friendly; primary accent #0A4B6F.",
        must_include=(),
        invariants=("Background plate only — no typography in the image.",),
    )
    text = serialize_openai_hero_prompt(brief)
    assert text.startswith("Create a photorealistic homepage hero background plate")
    assert "Subject:" in text
    assert "Composition:" in text
    assert "Invariants:" in text
    assert "Scene archetype:" not in text
    assert "Industry backdrop (modifier only):" not in text
    assert "Avoid:" not in text
    assert "photorealistic" in text.lower()


def test_composition_desktop_search_positive_safe_zone():
    comp = composition_block(tone_angle="search", inset_pct=40, is_mobile=False, has_cta=False)
    assert "left 40%" in comp
    assert "center-right" in comp
    assert "blank void" not in comp.lower()


@pytest.mark.asyncio
async def test_dental_compile_uses_openai_serializer():
    from app.payload.hero_models import HeroCandidatesRequest, hero_request_to_payload_v1
    from app.style.hero_prompt_compiler import compile_hero_triad_prompts
    from app.style.resolver import resolve_style_profile
    from tests.test_hero_candidates import _build_hero_request

    req = HeroCandidatesRequest.model_validate(_build_hero_request())
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    prompts = compile_hero_triad_prompts(req, profile)
    search = prompts[0].prompt
    assert prompts[0].compiler_version == "3.4"
    assert "Create a photorealistic homepage hero background plate" in search
    assert "dental clinic" in search.lower()
    assert "Invariants:" in search
    assert "Scene archetype:" not in search
    assert "Find a dentist" not in search
