"""s20 AC-3: merged avoid-list is global-first, de-duplicated, order-stable."""

from __future__ import annotations

import pytest


def test_global_first_and_deduped():
    try:
        from app.style.hero_archetypes import (  # type: ignore[import-not-found]
            GLOBAL_HERO_AVOID,
            hero_avoid_for_archetype,
        )
    except ImportError as exc:
        pytest.fail(f"AC-3: GLOBAL_HERO_AVOID + hero_avoid_for_archetype must be importable ({exc})")

    merged = hero_avoid_for_archetype("full_bleed_photo_overlay")
    assert len(merged) == len(set(merged)), "AC-3: merged avoid-list must be de-duplicated"
    assert merged[: len(GLOBAL_HERO_AVOID)] == tuple(GLOBAL_HERO_AVOID), (
        "AC-3: global avoid items must appear first, in order"
    )
