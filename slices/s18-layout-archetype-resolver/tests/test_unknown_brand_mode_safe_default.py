"""s18 AC-7: an unknown brand_mode falls back to the default archetype, never raises."""

from __future__ import annotations

import pytest


def test_unknown_brand_mode_safe_default():
    try:
        from app.layout.resolver import resolve_hero_layout_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: resolve_hero_layout_archetype must be importable ({exc})")

    decision = resolve_hero_layout_archetype(brand_mode="totally_made_up_mode", industry=None)
    assert decision.archetype == "split_copy_image", (
        "AC-7: unknown brand_mode must resolve to the default archetype, not raise"
    )
    assert decision.brand_mode_source == "default", (
        "AC-7: an unrouted brand_mode must record source='default'"
    )
