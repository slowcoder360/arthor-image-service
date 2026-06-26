"""s20 AC-4: an unknown/absent archetype falls back to the trimmed GLOBAL_HERO_AVOID."""

from __future__ import annotations

import pytest


def test_unknown_archetype_returns_global_only():
    try:
        from app.style.hero_archetypes import (  # type: ignore[import-not-found]
            GLOBAL_HERO_AVOID,
            hero_avoid_for_archetype,
        )
    except ImportError as exc:
        pytest.fail(f"AC-4: GLOBAL_HERO_AVOID + hero_avoid_for_archetype must be importable ({exc})")

    result = hero_avoid_for_archetype("not_a_real_archetype")
    assert tuple(result) == tuple(GLOBAL_HERO_AVOID), (
        "AC-4: an unknown archetype must fall back to the trimmed GLOBAL_HERO_AVOID unchanged"
    )
    assert all(isinstance(item, str) for item in GLOBAL_HERO_AVOID) and GLOBAL_HERO_AVOID, (
        "AC-1: GLOBAL_HERO_AVOID must remain a non-empty tuple of strings"
    )
