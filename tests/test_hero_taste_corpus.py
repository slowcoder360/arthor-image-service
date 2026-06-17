"""Tests for hero taste corpus resolution and fallback."""

from __future__ import annotations

import pytest

from app.style.hero_taste_corpus import (
    clear_corpus_cache,
    corpus_coverage,
    resolve_taste_corpus,
)


@pytest.fixture(autouse=True)
def _fresh_corpus_cache() -> None:
    clear_corpus_cache()
    yield
    clear_corpus_cache()


def test_resolve_dental_corpus_exact_label() -> None:
    triad = resolve_taste_corpus("dental", corpus_version="1.0")
    assert triad is not None
    assert triad.industry_label == "dental"
    assert len(triad.variants) == 3
    scenes = {v.variant_index: v.scene_archetype for v in triad.variants}
    assert scenes[0] == "threshold_invitation"
    assert scenes[1] == "shared_joy"
    assert scenes[2] == "confident_smile"


def test_resolve_unknown_industry_falls_back_to_general_services() -> None:
    triad = resolve_taste_corpus("boutique consulting firm", corpus_version="1.0")
    assert triad is not None
    assert triad.industry_label == "general_services"


def test_missing_corpus_version_returns_none() -> None:
    assert resolve_taste_corpus("dental", corpus_version="99.0") is None


def test_corpus_coverage_lists_seeded_industries() -> None:
    coverage = corpus_coverage(corpus_version="1.0")
    assert "dental" in coverage
    assert "general_services" in coverage
    assert coverage["dental"] == [0, 1, 2]
