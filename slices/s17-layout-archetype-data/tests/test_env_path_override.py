"""s17 AC-2: layout_archetype_data_path env override points the loader at a vendored copy."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_IN_REPO_DATA = _REPO_ROOT / "data" / "layout_archetypes"


def test_env_path_override_loads_alternate_copy(monkeypatch, tmp_path):
    try:
        from app.config import get_settings  # type: ignore[import-not-found]
        from app.layout.catalog import clear_layout_cache, load_layout_catalog  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: settings + catalog loader must be importable ({exc})")

    if not _IN_REPO_DATA.is_dir():
        pytest.fail("AC-1: data/layout_archetypes/ must exist in-repo as the default copy")

    vendored = tmp_path / "vendored_layout"
    shutil.copytree(_IN_REPO_DATA, vendored)

    monkeypatch.setenv("LAYOUT_ARCHETYPE_DATA_PATH", str(vendored))
    get_settings.cache_clear()
    clear_layout_cache()

    catalog = load_layout_catalog()
    assert catalog, "AC-2: loader must read the env-pointed vendored copy"

    settings = get_settings()
    assert getattr(settings, "layout_archetype_data_path", None) == str(vendored), (
        "AC-2: app.config.Settings must expose layout_archetype_data_path"
    )
