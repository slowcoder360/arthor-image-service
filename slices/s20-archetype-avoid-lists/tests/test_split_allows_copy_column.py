"""s20 AC-2: split_copy_image must NOT ban the blank left half — its copy column is intended."""

from __future__ import annotations

import pytest


def test_split_does_not_ban_copy_column():
    try:
        from app.style.hero_archetypes import hero_avoid_for_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: hero_avoid_for_archetype must be importable ({exc})")

    avoid = " | ".join(hero_avoid_for_archetype("split_copy_image")).lower()
    assert "blank left half" not in avoid, (
        "AC-2: split_copy_image must not ban a blank left half — the copy column is required geometry"
    )
