"""s02 AC-3: 001_external_media_assets.sql matches ADR-0005 DDL verbatim (text-level)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MIG_PATH = REPO_ROOT / "db" / "migrations" / "001_external_media_assets.sql"

REQUIRED_COLUMNS = [
    "id",
    "provider",
    "external_id",
    "model_version",
    "status",
    "expiration",
    "r2_key",
    "r2_url",
    "width",
    "height",
    "bytes",
    "metadata",
    "agent_run_id",
    "site_id",
    "created_at",
    "updated_at",
]

PROVIDER_ALLOWLIST = {"openai_image", "google_imagen", "google_nano_banana"}
STATUS_ALLOWLIST = {"pending", "generated", "uploaded", "failed", "superseded"}

REQUIRED_INDEXES = [
    "idx_ema_site_created",
    "idx_ema_agent_run",
    "idx_ema_status",
    "idx_ema_provider_model",
    "idx_ema_metadata_slot",
]


def _read_sql() -> str:
    if not MIG_PATH.exists():
        pytest.fail(f"AC-3: migration must exist at {MIG_PATH}")
    return MIG_PATH.read_text()


def test_migration_001_begin_commit_wrapped():
    sql = _read_sql()
    assert "BEGIN;" in sql, "AC-3: migration must be wrapped in BEGIN;"
    assert "COMMIT;" in sql, "AC-3: migration must be wrapped in COMMIT;"


@pytest.mark.parametrize("col", REQUIRED_COLUMNS)
def test_migration_001_has_column(col):
    sql = _read_sql()
    pattern = rf"\b{re.escape(col)}\b"
    assert re.search(pattern, sql), (
        f"AC-3: migration 001 must declare column '{col}' (ADR-0005)"
    )


def test_migration_001_provider_check_allowlist():
    sql = _read_sql()
    for value in PROVIDER_ALLOWLIST:
        assert value in sql, (
            f"AC-3: migration 001 provider CHECK must include '{value}'"
        )


def test_migration_001_status_check_allowlist():
    sql = _read_sql()
    for value in STATUS_ALLOWLIST:
        assert value in sql, (
            f"AC-3: migration 001 status CHECK must include '{value}'"
        )


@pytest.mark.parametrize("idx", REQUIRED_INDEXES)
def test_migration_001_has_index(idx):
    sql = _read_sql()
    assert idx in sql, f"AC-3: migration 001 must declare index '{idx}'"


def test_migration_001_fk_on_agent_run_id_cascade():
    sql = _read_sql().lower()
    assert "agent_run_id" in sql, "AC-3: agent_run_id column must be declared"
    assert "references agent_runs" in sql, (
        "AC-3: agent_run_id must be a FK to agent_runs(id)"
    )
    assert "on delete cascade" in sql, (
        "AC-3: agent_run_id FK must be ON DELETE CASCADE"
    )


def test_migration_001_no_fk_on_site_id():
    sql = _read_sql().lower()
    site_id_section = re.findall(r"site_id[^,]*", sql)
    fk_on_site = any("references" in segment for segment in site_id_section)
    assert not fk_on_site, (
        "AC-3: site_id must NOT be a FK (per ADR-0005 — sites table is in arthor-ai)"
    )
