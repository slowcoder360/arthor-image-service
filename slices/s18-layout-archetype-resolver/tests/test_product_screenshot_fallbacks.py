"""s18 AC-4: product_screenshot keeps its archetype/imagery but exposes deterministic fallbacks."""

from __future__ import annotations

import pytest


def test_product_screenshot_decision_exposes_fallbacks():
    try:
        from app.layout.resolver import resolve_hero_layout_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: resolve_hero_layout_archetype must be importable ({exc})")

    decision = resolve_hero_layout_archetype(brand_mode="tech_saas", industry=None)
    assert decision.archetype == "product_screenshot", (
        "AC-4: tech_saas resolves to the product_screenshot decision"
    )
    assert decision.imagery_type == "product_ui", (
        "AC-4: product_screenshot imagery_type must be product_ui"
    )
    assert decision.imagery_fallbacks == ("abstract_gradient_3d", "centered_copy_cta"), (
        "AC-4: product_screenshot must expose imagery_fallbacks "
        "(abstract_gradient_3d, centered_copy_cta) for the never-synthesize rule"
    )
