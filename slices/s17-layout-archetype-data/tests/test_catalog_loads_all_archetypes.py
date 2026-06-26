"""s17 AC-1/AC-5: the vendored catalog loads all archetypes with a valid imagery_type."""

from __future__ import annotations

import pytest

EXPECTED_ARCHETYPES = {
    "split_copy_image",
    "full_bleed_photo_overlay",
    "centered_copy_cta",
    "abstract_gradient_3d",
    "typographic_no_image",
    "product_screenshot",
}

VALID_IMAGERY_TYPES = {
    "real_photo",
    "product_ui",
    "generative_abstract",
    "abstract_or_none",
    "none",
}


def test_catalog_loads_all_archetypes():
    try:
        from app.layout.catalog import load_layout_catalog  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app.layout.catalog.load_layout_catalog must be importable ({exc})")

    catalog = load_layout_catalog()
    ids = {entry.archetype for entry in catalog}
    assert ids == EXPECTED_ARCHETYPES, (
        f"AC-1: catalog must define exactly {sorted(EXPECTED_ARCHETYPES)}; got {sorted(ids)}"
    )


def test_every_archetype_has_valid_imagery_type():
    try:
        from app.layout.catalog import load_layout_catalog  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: load_layout_catalog must be importable ({exc})")

    for entry in load_layout_catalog():
        assert entry.imagery_type in VALID_IMAGERY_TYPES, (
            f"AC-1/AC-5: archetype {entry.archetype!r} has invalid imagery_type "
            f"{entry.imagery_type!r}; valid: {sorted(VALID_IMAGERY_TYPES)}"
        )
