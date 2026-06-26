"""s18 AC-6: the resolver stays decoupled from scene/payload/route/provider code."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_RESOLVER_SRC = _REPO_ROOT / "app" / "layout" / "resolver.py"

FORBIDDEN = (
    "app.style.hero_visual_strategy",
    "app.style.hero_archetypes",
    "app.payload.hero_models",
    "app.routes",
    "app.providers",
)


def test_resolver_module_has_no_forbidden_imports():
    if not _RESOLVER_SRC.is_file():
        pytest.fail("AC-1: app/layout/resolver.py must exist")
    src = _RESOLVER_SRC.read_text(encoding="utf-8")
    for mod in FORBIDDEN:
        assert mod not in src, (
            f"AC-6: app/layout/resolver.py must not import {mod} "
            "(must lift-and-shift to the planning brain unchanged)"
        )
