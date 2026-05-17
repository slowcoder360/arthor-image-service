"""s02 AC-3..AC-5 smoke: against a clean dev DB, apply 001 → 002 → 003 and check information_schema."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_migrations_apply_creates_expected_tables_and_columns():
    try:
        import asyncpg
    except ImportError as exc:
        pytest.fail(f"asyncpg is not installed: {exc}")

    files = [
        MIGRATIONS_DIR / "001_external_media_assets.sql",
        MIGRATIONS_DIR / "002_image_request_payloads.sql",
        MIGRATIONS_DIR / "003_tool_calls_cost_columns.sql",
    ]
    for f in files:
        if not f.exists():
            pytest.fail(f"AC-3..5: migration {f.name} must exist before smoke can apply")

    dsn = os.environ["DATABASE_URL"]
    conn = await asyncpg.connect(dsn)
    try:
        for path in files:
            sql = path.read_text()
            await conn.execute(sql)

        ema_cols = {
            row["column_name"]
            for row in await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'external_media_assets'"
            )
        }
        for col in (
            "id",
            "provider",
            "external_id",
            "model_version",
            "status",
            "expiration",
            "r2_key",
            "metadata",
            "agent_run_id",
            "site_id",
        ):
            assert col in ema_cols, (
                f"AC-3 smoke: external_media_assets must have column '{col}' after migration"
            )

        irp_cols = {
            row["column_name"]
            for row in await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'image_request_payloads'"
            )
        }
        for col in (
            "id",
            "agent_run_id",
            "payload_version",
            "payload",
            "payload_hash",
            "idempotency_key",
            "source",
            "created_at",
        ):
            assert col in irp_cols, (
                f"AC-4 smoke: image_request_payloads must have column '{col}' after migration"
            )

        tool_calls_cols = {
            row["column_name"]
            for row in await conn.fetch(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'tool_calls'"
            )
        }
        for col in ("cost_cents", "provider", "model_version"):
            assert col in tool_calls_cols, (
                f"AC-5 smoke: tool_calls must have column '{col}' after migration 003"
            )
    finally:
        await conn.close()
