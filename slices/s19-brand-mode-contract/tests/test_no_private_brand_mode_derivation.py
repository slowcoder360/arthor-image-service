"""s19 AC-2: the route must call the resolver, not keep a private industry→mode map."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ROUTE_SRC = _REPO_ROOT / "app" / "routes" / "hero_candidates.py"


def test_route_uses_resolver_and_has_no_private_map():
    if not _ROUTE_SRC.is_file():
        pytest.fail("AC-2: app/routes/hero_candidates.py must exist")
    src = _ROUTE_SRC.read_text(encoding="utf-8")

    assert "resolve_hero_layout_archetype" in src, (
        "AC-2: the route must compute the decision via resolve_hero_layout_archetype"
    )
    # Guard against a private fork of the industry→mode mapping living in the route.
    assert "industry_brand_mode" not in src and "BRAND_MODE_DEFAULT_LAYOUT" not in src, (
        "AC-2: the route must not embed its own brand_mode/industry mapping — "
        "that lives only in the vendored data + resolver"
    )
