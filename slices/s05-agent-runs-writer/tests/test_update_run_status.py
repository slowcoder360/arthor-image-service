"""s05 AC-2: update_run_status transitions running → ok; finished sets finished_at; metadata_patch merges."""

from __future__ import annotations

import uuid

import pytest

from _db_helpers import make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_update_run_status_finished_ok_sets_finished_at_and_merges_metadata():
    try:
        from app.runs.agent_runs import (  # type: ignore[import-not-found]
            insert_pending_run,
            update_run_status,
        )
    except ImportError as exc:
        pytest.fail(f"AC-2: writers must be importable ({exc})")

    pool = await make_pool()
    try:
        run_id = await insert_pending_run(
            pool,
            run_type="image_pack_generation",
            site_id=uuid.uuid4(),
            metadata={"k1": "v1"},
        )
        await update_run_status(
            pool,
            run_id,
            status="ok",
            finished=True,
            metadata_patch={"k2": "v2"},
        )
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status, finished_at, metadata FROM agent_runs WHERE id = $1",
                run_id,
            )
        assert row["status"] == "ok", "AC-2: status must transition to 'ok'"
        assert row["finished_at"] is not None, (
            "AC-2: finished=True must set finished_at"
        )
        import json

        meta = (
            row["metadata"]
            if isinstance(row["metadata"], dict)
            else json.loads(row["metadata"])
        )
        assert meta.get("k1") == "v1", (
            "AC-2: metadata_patch must shallow-merge (existing keys preserved)"
        )
        assert meta.get("k2") == "v2", "AC-2: metadata_patch must add new keys"

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()


@pytest.mark.asyncio
async def test_update_run_status_rejects_unknown_status_without_db():
    try:
        from app.runs.agent_runs import update_run_status  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: update_run_status must be importable ({exc})")

    class _PoolStub:
        def __getattr__(self, name):
            raise AssertionError(
                f"AC-2: writer must reject unknown status BEFORE touching pool.{name}"
            )

    with pytest.raises(ValueError):
        await update_run_status(_PoolStub(), uuid.uuid4(), status="weird")
