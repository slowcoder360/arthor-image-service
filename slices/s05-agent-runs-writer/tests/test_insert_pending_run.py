"""s05 AC-1: insert_pending_run inserts a 'running' row with started_at + cost_cents=0."""

from __future__ import annotations

import uuid

import pytest

from _db_helpers import make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_insert_pending_run_creates_running_row():
    try:
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-1: `app.runs.agent_runs.insert_pending_run` must be importable ({exc})"
        )

    pool = await make_pool()
    try:
        site_id = uuid.uuid4()
        run_id = await insert_pending_run(
            pool,
            run_type="image_pack_generation",
            site_id=site_id,
            metadata={"foo": "bar"},
        )
        assert isinstance(run_id, uuid.UUID), "AC-1: must return a UUID"
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, run_type, status, started_at, cost_cents, metadata "
                "FROM agent_runs WHERE id = $1",
                run_id,
            )
        assert row is not None, "AC-1: row must be persisted"
        assert row["status"] == "running", (
            f"AC-1: status must be 'running', got {row['status']!r}"
        )
        assert row["run_type"] == "image_pack_generation", (
            "AC-1: run_type must round-trip"
        )
        assert row["started_at"] is not None, (
            "AC-1: started_at must be set on insert"
        )
        assert row["cost_cents"] == 0, "AC-1: cost_cents must default to 0"

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()
