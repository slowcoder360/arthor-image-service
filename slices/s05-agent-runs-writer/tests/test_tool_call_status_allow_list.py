"""s05 AC-4: tool_calls.status allow-list — {ok, error, skipped}; 'running' rejected."""

from __future__ import annotations

import uuid

import pytest

from _db_helpers import make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_tool_call_status_running_rejected_via_db_check_or_writer():
    try:
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runs.tool_calls import insert_tool_call  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: writers must be importable ({exc})")

    pool = await make_pool()
    try:
        run_id = await insert_pending_run(
            pool, run_type="image_pack_generation", site_id=uuid.uuid4()
        )
        with pytest.raises(Exception):
            await insert_tool_call(
                pool,
                run_id=run_id,
                tool_name="openai.images.generate",
                args={},
                result={},
                status="running",
                latency_ms=0,
                cost_cents=0,
                provider=None,
                model_version=None,
            )
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()


@pytest.mark.parametrize("status", ["ok", "error", "skipped"])
@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_tool_call_documented_statuses_accepted(status):
    try:
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runs.tool_calls import insert_tool_call  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: writers must be importable ({exc})")

    pool = await make_pool()
    try:
        run_id = await insert_pending_run(
            pool, run_type="image_pack_generation", site_id=uuid.uuid4()
        )
        tc_id = await insert_tool_call(
            pool,
            run_id=run_id,
            tool_name="t",
            args={},
            result={},
            status=status,
            latency_ms=1,
            cost_cents=0,
            provider=None,
            model_version=None,
        )
        assert tc_id > 0, f"AC-4: status='{status}' must be accepted"
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM tool_calls WHERE id = $1", tc_id)
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()
