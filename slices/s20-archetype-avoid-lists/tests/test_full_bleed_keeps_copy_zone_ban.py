"""s20 AC-2/AC-3: full_bleed_photo_overlay still bans the blank left half."""

from __future__ import annotations

import pytest


def test_full_bleed_keeps_copy_zone_ban():
    try:
        from app.style.hero_archetypes import hero_avoid_for_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: hero_avoid_for_archetype must be importable ({exc})")

    avoid = " | ".join(hero_avoid_for_archetype("full_bleed_photo_overlay")).lower()
    assert "blank left half" in avoid, (
        "AC-2: full_bleed_photo_overlay must still ban the blank left half / empty copy void"
    )
