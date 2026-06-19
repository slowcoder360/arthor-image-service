"""Visual triad: three distinct scene archetypes per industry × variant_index."""

from __future__ import annotations

import pytest

from app.payload.hero_models import HeroCandidatesRequest
from app.style.hero_archetypes import resolve_industry
from app.style.hero_visual_strategy import (
    INDUSTRY_VISUAL_TRIAD,
    resolve_hero_visual_strategy,
    resolve_scene_archetype,
)
from tests.test_hero_candidates import _build_hero_request

_INDUSTRY_FIXTURES: tuple[tuple[str, str], ...] = (
    ("dental", "dental"),
    ("personal injury law", "legal"),
    ("hvac repair", "home_services"),
    ("physical therapy clinic", "healthcare"),
    ("landscaping", "outdoor_services"),
    ("consulting", "general_services"),
)


def _req_for_industry(industry: str) -> HeroCandidatesRequest:
    raw = _build_hero_request()
    raw["business"]["industry"] = industry
    return HeroCandidatesRequest.model_validate(raw)


@pytest.mark.parametrize("industry_input,expected_label", _INDUSTRY_FIXTURES)
def test_industry_visual_triad_has_three_distinct_archetypes(
    industry_input: str,
    expected_label: str,
) -> None:
    triad = INDUSTRY_VISUAL_TRIAD[expected_label]
    assert len(triad) == 3
    assert len(set(triad)) == 3, f"{expected_label}: archetypes must be pairwise distinct"


@pytest.mark.parametrize("industry_input,expected_label", _INDUSTRY_FIXTURES)
def test_scene_selection_uses_variant_index_not_tone(
    industry_input: str,
    expected_label: str,
) -> None:
    req = _req_for_industry(industry_input)
    assert resolve_industry(industry_input).label == expected_label
    triad = INDUSTRY_VISUAL_TRIAD[expected_label]
    for index in range(3):
        assert resolve_scene_archetype(req, index) == triad[index]


def test_variant_index_primary_ignores_tone_angle() -> None:
    raw = _build_hero_request()
    for index, variant in enumerate(raw["variants"]):
        variant["tone_angle"] = "offer" if index == 0 else "search"
    req = HeroCandidatesRequest.model_validate(raw)
    triad = INDUSTRY_VISUAL_TRIAD["dental"]
    for index in range(3):
        assert resolve_scene_archetype(req, index) == triad[index]


def test_hero_visual_strategy_metadata_reflects_index_driven_scenes() -> None:
    req = _req_for_industry("dental")
    strategy = resolve_hero_visual_strategy(req)
    assert strategy.industry_label == "dental"
    assert len(strategy.variants) == 3
    scenes = [v.scene_archetype for v in strategy.variants]
    assert len(set(scenes)) == 3
    for index, variant in enumerate(strategy.variants):
        assert variant.variant_index == index
        assert variant.scene_archetype == INDUSTRY_VISUAL_TRIAD["dental"][index]
