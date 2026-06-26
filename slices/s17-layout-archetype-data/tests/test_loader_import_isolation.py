"""s17 AC-4: the loader is pure data access — no scene/payload/provider imports."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CATALOG_SRC = _REPO_ROOT / "app" / "layout" / "catalog.py"

FORBIDDEN = (
    "app.style.hero_visual_strategy",
    "app.style.hero_archetypes",
    "app.payload",
    "app.providers",
    "app.routes",
)


def test_catalog_module_has_no_forbidden_imports():
    if not _CATALOG_SRC.is_file():
        pytest.fail("AC-3: app/layout/catalog.py must exist")
    src = _CATALOG_SRC.read_text(encoding="utf-8")
    for mod in FORBIDDEN:
        assert mod not in src, (
            f"AC-4: app/layout/catalog.py must not import {mod} (pure data access only)"
        )
