"""s02 AC-7: docs/migrations.md documents the apply order, dev-only rule, W11 note."""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
DOC_PATH = REPO_ROOT / "docs" / "migrations.md"


def test_migrations_doc_exists():
    assert DOC_PATH.exists(), f"AC-7: docs/migrations.md must exist at {DOC_PATH}"


def test_migrations_doc_documents_apply_order():
    if not DOC_PATH.exists():
        pytest.fail("AC-7: docs/migrations.md must exist")
    text = DOC_PATH.read_text()
    assert "001" in text and "002" in text and "003" in text, (
        "AC-7: docs/migrations.md must reference all three migrations 001/002/003"
    )


def test_migrations_doc_psql_command():
    if not DOC_PATH.exists():
        pytest.fail("AC-7: docs/migrations.md must exist")
    text = DOC_PATH.read_text()
    assert "psql" in text, (
        "AC-7: docs/migrations.md must show the `psql ... -f db/migrations/...` apply command"
    )
    assert "db/migrations" in text, (
        "AC-7: docs/migrations.md must reference the db/migrations/ path"
    )


def test_migrations_doc_dev_only_w11_warning():
    if not DOC_PATH.exists():
        pytest.fail("AC-7: docs/migrations.md must exist")
    text = DOC_PATH.read_text()
    assert "W11" in text, (
        "AC-7: docs/migrations.md must call out W11 ownership of prod"
    )
    assert "dev" in text.lower(), (
        "AC-7: docs/migrations.md must restrict apply to dev (Neon branch)"
    )
