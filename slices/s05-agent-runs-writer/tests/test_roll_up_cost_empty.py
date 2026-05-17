"""s05 AC-6: roll_up_cost on a run with zero tool_calls returns 0 without error."""

from __future__ import annotations

import uuid

import pytest

from _db_helpers import make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_roll_up_cost_zero_tool_calls_returns_zero():
    try:
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runs.cost_rollup import roll_up_cost  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: writers must be importable ({exc})")

    pool = await make_pool()
    try:
        run_id = await insert_pending_run(
            pool, run_type="image_pack_generation", site_id=uuid.uuid4()
        )
        total = await roll_up_cost(pool, run_id)
        assert total == 0, (
            f"AC-6: roll_up_cost on a run with zero tool_calls must return 0; got {total}"
        )

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()
