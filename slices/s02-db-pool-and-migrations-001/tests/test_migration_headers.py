"""s02 AC-6: every migration has the standard header and BEGIN;/COMMIT; wrapping."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

EXPECTED_FILES = [
    "001_external_media_assets.sql",
    "002_image_request_payloads.sql",
    "003_tool_calls_cost_columns.sql",
]


@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_migration_file_has_standard_header(filename):
    path = MIGRATIONS_DIR / filename
    if not path.exists():
        pytest.fail(f"AC-6: migration file must exist at {path}")
    text = path.read_text()
    assert text.lstrip().startswith("-- Migration"), (
        f"AC-6: {filename} must start with the '-- Migration NNN: ...' header"
    )
    assert "dev Neon branch" in text or "dev neon branch" in text.lower(), (
        f"AC-6: {filename} header must reference the dev Neon branch rule"
    )
    assert "W11" in text, (
        f"AC-6: {filename} header must reference W11 coordination for prod"
    )


@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_migration_wrapped_in_begin_commit(filename):
    path = MIGRATIONS_DIR / filename
    if not path.exists():
        pytest.fail(f"AC-6: migration file must exist at {path}")
    text = path.read_text()
    assert "BEGIN;" in text, f"AC-6: {filename} must include BEGIN;"
    assert "COMMIT;" in text, f"AC-6: {filename} must include COMMIT;"
