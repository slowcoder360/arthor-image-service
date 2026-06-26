"""s18 AC-3: no brand_mode and no industry → documented safe default."""

from __future__ import annotations

import pytest


def test_default_when_no_signal():
    try:
        from app.layout.resolver import resolve_hero_layout_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: resolve_hero_layout_archetype must be importable ({exc})")

    decision = resolve_hero_layout_archetype(brand_mode=None, industry=None)
    assert decision.archetype == "split_copy_image", (
        "AC-3: with no signal the resolver must default to split_copy_image"
    )
    assert decision.brand_mode_source == "default", (
        "AC-3: the no-signal path must record brand_mode_source='default'"
    )
