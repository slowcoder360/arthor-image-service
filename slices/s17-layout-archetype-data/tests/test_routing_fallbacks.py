"""s17 AC-1: brand_mode routing + the never-synthesize-a-screenshot fallback chain."""

from __future__ import annotations

import pytest


def test_brand_mode_routing_has_known_defaults():
    try:
        from app.layout.catalog import load_brand_mode_routing  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: load_brand_mode_routing must be importable ({exc})")

    routing = load_brand_mode_routing()
    assert routing.default_for("ai_platform") == "centered_copy_cta", (
        "AC-1: ai_platform must route to centered_copy_cta"
    )
    assert routing.default_for("local_service") == "split_copy_image", (
        "AC-1: local_service must route to split_copy_image"
    )


def test_product_screenshot_fallback_never_synthesizes():
    try:
        from app.layout.catalog import load_brand_mode_routing  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: load_brand_mode_routing must be importable ({exc})")

    routing = load_brand_mode_routing()
    fallbacks = routing.fallbacks_for("product_screenshot")
    assert "product_screenshot" not in fallbacks, (
        "AC-1: product_screenshot must never appear in its own fallback chain "
        "(no synthetic screenshots)"
    )
    assert tuple(fallbacks)[:1] == ("abstract_gradient_3d",), (
        "AC-1: product_screenshot must fall back to abstract_gradient_3d first"
    )
