"""s17 AC-5: a catalog with an unknown imagery_type fails fast with LayoutCatalogError."""

from __future__ import annotations

import pytest


def test_unknown_imagery_type_raises(monkeypatch, tmp_path):
    try:
        from app.config import get_settings  # type: ignore[import-not-found]
        from app.layout.catalog import (  # type: ignore[import-not-found]
            LayoutCatalogError,
            clear_layout_cache,
            load_layout_catalog,
        )
    except ImportError as exc:
        pytest.fail(f"AC-5: LayoutCatalogError + loader must be importable ({exc})")

    bad_dir = tmp_path / "bad_layout"
    bad_dir.mkdir()
    (bad_dir / "catalog.yaml").write_text(
        "catalog_version: '1.0'\n"
        "archetypes:\n"
        "  split_copy_image:\n"
        "    imagery_type: not_a_real_type\n"
        "    scene_catalog_eligible: true\n"
        "    structure: x\n"
        "    avoid: []\n",
        encoding="utf-8",
    )
    (bad_dir / "brand_mode_routing.yaml").write_text("defaults: {}\nfallbacks: {}\n", encoding="utf-8")
    (bad_dir / "industry_brand_mode.yaml").write_text("map: {}\n", encoding="utf-8")

    monkeypatch.setenv("LAYOUT_ARCHETYPE_DATA_PATH", str(bad_dir))
    get_settings.cache_clear()
    clear_layout_cache()

    with pytest.raises(LayoutCatalogError):
        load_layout_catalog()
