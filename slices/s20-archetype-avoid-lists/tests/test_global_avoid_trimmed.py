"""s20 AC-1: copy-zone bans are removed from the global avoid tuple."""

from __future__ import annotations

import pytest


def test_global_avoid_no_longer_bans_copy_zone():
    try:
        from app.style.hero_archetypes import GLOBAL_HERO_AVOID  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: GLOBAL_HERO_AVOID must be importable ({exc})")

    joined = " | ".join(GLOBAL_HERO_AVOID).lower()
    assert "blank left half" not in joined, (
        "AC-1: the 'blank left half' ban must move off the global list (it is required "
        "geometry for split_copy_image)"
    )
    assert "copy-zone wall" not in joined and "copy zone wall" not in joined, (
        "AC-1: the 'sterile copy-zone wall' ban must move off the global list"
    )
