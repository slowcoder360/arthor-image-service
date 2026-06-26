"""s20 AC-5: abstract/typographic archetypes ban people + the indigo/purple gradient slop tell."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize("archetype", ["abstract_gradient_3d", "typographic_no_image"])
def test_no_people_in_abstract_archetypes(archetype):
    try:
        from app.style.hero_archetypes import hero_avoid_for_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: hero_avoid_for_archetype must be importable ({exc})")

    avoid = " | ".join(hero_avoid_for_archetype(archetype)).lower()
    assert "people" in avoid or "human" in avoid, (
        f"AC-5: {archetype} must ban people / human subjects"
    )


def test_abstract_bans_purple_gradient():
    try:
        from app.style.hero_archetypes import hero_avoid_for_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: hero_avoid_for_archetype must be importable ({exc})")

    avoid = " | ".join(hero_avoid_for_archetype("abstract_gradient_3d")).lower()
    assert "purple" in avoid or "indigo" in avoid, (
        "AC-5: abstract_gradient_3d must ban the indigo/purple gradient (the #1 AI-slop tell)"
    )
