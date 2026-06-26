"""s18 AC-5: same inputs → equal decisions (deterministic, no randomness/time/IO)."""

from __future__ import annotations

import pytest


def test_resolver_is_deterministic():
    try:
        from app.layout.resolver import resolve_hero_layout_archetype  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: resolve_hero_layout_archetype must be importable ({exc})")

    a = resolve_hero_layout_archetype(brand_mode="dev_tools", industry="dev tools")
    b = resolve_hero_layout_archetype(brand_mode="dev_tools", industry="dev tools")
    assert a == b, "AC-5: repeated calls with the same inputs must return equal decisions"
