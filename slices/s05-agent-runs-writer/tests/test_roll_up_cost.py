"""s05 AC-6: roll_up_cost sums tool_calls.cost_cents into agent_runs.cost_cents and sets finished_at."""

from __future__ import annotations

import uuid

import pytest

from _db_helpers import make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_roll_up_cost_sums_three_tool_calls():
    try:
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runs.cost_rollup import roll_up_cost  # type: ignore[import-not-found]
        from app.runs.tool_calls import insert_tool_call  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: writers must be importable ({exc})")

    pool = await make_pool()
    try:
        run_id = await insert_pending_run(
            pool, run_type="image_pack_generation", site_id=uuid.uuid4()
        )
        tc_ids = []
        for cents in (5, 7, 11):
            tc_id = await insert_tool_call(
                pool,
                run_id=run_id,
                tool_name="t",
                args={},
                result={},
                status="ok",
                latency_ms=1,
                cost_cents=cents,
                provider="openai_image",
                model_version="gpt-image-1",
            )
            tc_ids.append(tc_id)

        total = await roll_up_cost(pool, run_id)
        assert total == 23, (
            f"AC-6: roll_up_cost must return SUM(cost_cents)=23; got {total}"
        )

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT cost_cents, finished_at FROM agent_runs WHERE id = $1", run_id
            )
        assert row["cost_cents"] == 23, (
            "AC-6: agent_runs.cost_cents must be updated by roll_up_cost"
        )
        assert row["finished_at"] is not None, (
            "AC-6: roll_up_cost must set finished_at = COALESCE(finished_at, now())"
        )

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM tool_calls WHERE id = ANY($1::bigint[])", tc_ids)
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()
