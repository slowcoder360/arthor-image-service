"""s02 AC-5: 003_tool_calls_cost_columns.sql — additive ALTERs only; honors run_id (NOT agent_run_id)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MIG_PATH = REPO_ROOT / "db" / "migrations" / "003_tool_calls_cost_columns.sql"


def _read_sql() -> str:
    if not MIG_PATH.exists():
        pytest.fail(f"AC-5: migration must exist at {MIG_PATH}")
    return MIG_PATH.read_text()


def test_migration_003_begin_commit_wrapped():
    sql = _read_sql()
    assert "BEGIN;" in sql and "COMMIT;" in sql, "AC-5: must be wrapped in BEGIN;/COMMIT;"


def test_migration_003_only_alter_table_and_create_index_statements():
    sql = _read_sql()
    body = re.sub(r"--.*", "", sql)
    statements = [
        s.strip()
        for s in body.split(";")
        if s.strip()
        and s.strip().upper() not in ("BEGIN", "COMMIT")
    ]
    for stmt in statements:
        upper = stmt.upper().lstrip()
        assert upper.startswith("ALTER TABLE") or upper.startswith("CREATE INDEX"), (
            f"AC-5: migration 003 must contain only ALTER TABLE / CREATE INDEX statements; "
            f"found: {stmt[:80]!r}"
        )


def test_migration_003_adds_cost_cents_with_default_zero():
    sql = _read_sql()
    pattern = re.compile(
        r"ADD COLUMN\s+IF NOT EXISTS\s+cost_cents\s+int\s+NOT NULL\s+DEFAULT\s+0",
        re.IGNORECASE,
    )
    assert pattern.search(sql), (
        "AC-5: must `ADD COLUMN IF NOT EXISTS cost_cents int NOT NULL DEFAULT 0`"
    )


def test_migration_003_adds_provider_nullable():
    sql = _read_sql()
    pattern = re.compile(
        r"ADD COLUMN\s+IF NOT EXISTS\s+provider\s+text\s+NULL",
        re.IGNORECASE,
    )
    assert pattern.search(sql), "AC-5: must `ADD COLUMN IF NOT EXISTS provider text NULL`"


def test_migration_003_adds_model_version_nullable():
    sql = _read_sql()
    pattern = re.compile(
        r"ADD COLUMN\s+IF NOT EXISTS\s+model_version\s+text\s+NULL",
        re.IGNORECASE,
    )
    assert pattern.search(sql), (
        "AC-5: must `ADD COLUMN IF NOT EXISTS model_version text NULL`"
    )


def test_migration_003_creates_provider_index():
    sql = _read_sql()
    pattern = re.compile(
        r"CREATE INDEX\s+IF NOT EXISTS\s+idx_tool_calls_provider\s+ON\s+tool_calls\s*\(provider\)",
        re.IGNORECASE,
    )
    assert pattern.search(sql), (
        "AC-5: must `CREATE INDEX IF NOT EXISTS idx_tool_calls_provider ON tool_calls (provider)`"
    )


def test_migration_003_does_not_introduce_agent_run_id_typo():
    sql = _read_sql()
    assert "agent_run_id" not in sql, (
        "AC-5 (ADR-0004 critical drift): migration 003 must NOT mention 'agent_run_id'; "
        "the column on tool_calls is `run_id`."
    )
