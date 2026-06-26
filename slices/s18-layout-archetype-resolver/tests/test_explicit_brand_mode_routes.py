"""s18 AC-1/AC-3: explicit brand_mode routes deterministically; source is 'explicit'."""

from __future__ import annotations

import pytest


def test_explicit_brand_mode_routes():
    try:
        from app.layout.resolver import resolve_hero_layout_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: resolve_hero_layout_archetype must be importable ({exc})")

    decision = resolve_hero_layout_archetype(brand_mode="ai_platform", industry="anything")
    assert decision.archetype == "centered_copy_cta", (
        "AC-1: brand_mode=ai_platform must resolve to centered_copy_cta"
    )
    assert decision.brand_mode == "ai_platform"
    assert decision.brand_mode_source == "explicit", (
        "AC-3: an explicit brand_mode must record brand_mode_source='explicit'"
    )
