"""s17 AC-6: PHOTO_LAYOUTS is derived from scene_catalog_eligible, not hardcoded."""

from __future__ import annotations

import pytest


def test_photo_layouts_derived_from_eligibility():
    try:
        from app.layout.catalog import PHOTO_LAYOUTS, load_layout_catalog  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: PHOTO_LAYOUTS + load_layout_catalog must be importable ({exc})")

    eligible = {e.archetype for e in load_layout_catalog() if e.scene_catalog_eligible}
    assert set(PHOTO_LAYOUTS) == eligible, (
        "AC-6: PHOTO_LAYOUTS must equal the set of scene_catalog_eligible archetypes"
    )
    assert set(PHOTO_LAYOUTS) == {"split_copy_image", "full_bleed_photo_overlay"}, (
        "AC-6: only split_copy_image + full_bleed_photo_overlay are photo-eligible in v1"
    )
