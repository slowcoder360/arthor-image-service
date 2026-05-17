"""s02 AC-4: 002_image_request_payloads.sql — UNIQUE on idempotency_key, two indexes, FK CASCADE."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MIG_PATH = REPO_ROOT / "db" / "migrations" / "002_image_request_payloads.sql"


def _read_sql() -> str:
    if not MIG_PATH.exists():
        pytest.fail(f"AC-4: migration must exist at {MIG_PATH}")
    return MIG_PATH.read_text()


def test_migration_002_begin_commit_wrapped():
    sql = _read_sql()
    assert "BEGIN;" in sql and "COMMIT;" in sql, "AC-4: must be wrapped in BEGIN;/COMMIT;"


def test_migration_002_unique_constraint_on_idempotency_key():
    sql = _read_sql().lower()
    assert "image_request_payloads_idem_unique" in sql, (
        "AC-4: must include UNIQUE constraint named 'image_request_payloads_idem_unique'"
    )
    assert "idempotency_key" in sql, "AC-4: idempotency_key column must be declared"


def test_migration_002_required_columns():
    sql = _read_sql()
    for col in [
        "id",
        "agent_run_id",
        "payload_version",
        "payload",
        "payload_hash",
        "idempotency_key",
        "source",
        "created_at",
    ]:
        assert col in sql, f"AC-4: migration 002 must declare column '{col}'"


def test_migration_002_indexes():
    sql = _read_sql()
    for idx in ("idx_irp_agent_run", "idx_irp_payload_hash"):
        assert idx in sql, f"AC-4: migration 002 must declare index '{idx}'"


def test_migration_002_fk_cascade_on_agent_run_id():
    sql = _read_sql().lower()
    assert "references agent_runs" in sql, (
        "AC-4: agent_run_id must be a FK to agent_runs(id)"
    )
    assert "on delete cascade" in sql, (
        "AC-4: agent_run_id FK must be ON DELETE CASCADE"
    )


def test_migration_002_source_default_arthor_ai():
    sql = _read_sql()
    assert re.search(r"source\s+text\s+NOT NULL\s+DEFAULT\s+'arthor-ai'", sql, re.IGNORECASE), (
        "AC-4: source column must be `text NOT NULL DEFAULT 'arthor-ai'`"
    )
