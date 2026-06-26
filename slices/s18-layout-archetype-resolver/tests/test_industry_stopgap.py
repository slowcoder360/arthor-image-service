"""s18 AC-3: with no brand_mode, derive it from the industry map (stopgap)."""

from __future__ import annotations

import pytest


def test_industry_stopgap_derivation():
    try:
        from app.layout.resolver import resolve_hero_layout_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: resolve_hero_layout_archetype must be importable ({exc})")

    decision = resolve_hero_layout_archetype(brand_mode=None, industry="AI marketing agency")
    assert decision.brand_mode_source == "industry_stopgap", (
        "AC-3: deriving brand_mode from industry must record source='industry_stopgap'"
    )
    assert decision.brand_mode in {"agency", "ai_platform", "tech_saas", "dev_tools"}, (
        f"AC-3: an AI/agency industry must map to a tech brand_mode; got {decision.brand_mode!r}"
    )
