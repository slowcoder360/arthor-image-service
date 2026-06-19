"""Tests for hero taste corpus resolution and fallback."""

from __future__ import annotations

from pathlib import Path

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


def test_v2_resolves_slug_by_longest_match_key(tmp_path: Path, monkeypatch) -> None:
    from app.style import hero_taste_corpus as corpus_mod

    v2_dir = tmp_path / "hero_taste_corpus" / "v2"
    v2_dir.mkdir(parents=True)
    (v2_dir / "hvac.yaml").write_text(
        """
corpus_version: '2.0'
slug: hvac
industry_label: home_services
match_keys:
  - hvac repair
  - hvac
variants:
  - variant_index: 0
    scene_archetype: threshold_invitation
    hero_job: trust
    r2_key: hero-candidates/test/0.png
    public_url: https://cdn.example/hvac0.png
    style_profile_fragment: {lighting: soft}
    compiler_version: '4.1'
    approved_at: '2026-06-18'
    approved_by: justin
  - variant_index: 1
    scene_archetype: desk_side_guidance
    hero_job: experience
    r2_key: hero-candidates/test/1.png
    public_url: https://cdn.example/hvac1.png
    style_profile_fragment: {lighting: soft}
    compiler_version: '4.1'
    approved_at: '2026-06-18'
    approved_by: justin
  - variant_index: 2
    scene_archetype: environment_warmth
    hero_job: outcome
    r2_key: hero-candidates/test/2.png
    public_url: https://cdn.example/hvac2.png
    style_profile_fragment: {lighting: soft}
    compiler_version: '4.1'
    approved_at: '2026-06-18'
    approved_by: justin
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(corpus_mod, "CORPUS_DATA_ROOT", tmp_path / "hero_taste_corpus")
    clear_corpus_cache()
    triad = resolve_taste_corpus("hvac repair", corpus_version="2.0")
    assert triad is not None
    assert triad.slug == "hvac"
    assert triad.industry_label == "home_services"
    assert len(triad.variants) == 3


def test_v2_falls_back_to_v1_coarse_when_no_slug_match() -> None:
    triad = resolve_taste_corpus("boutique consulting firm", corpus_version="2.0")
    assert triad is not None
    assert triad.industry_label == "general_services"
    assert triad.corpus_version == "1.0"


def test_corpus_coverage_lists_seeded_industries() -> None:
    coverage = corpus_coverage(corpus_version="1.0")
    assert "dental" in coverage
    assert "general_services" in coverage
    assert coverage["dental"] == [0, 1, 2]
