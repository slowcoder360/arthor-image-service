"""s15 AC-1: cost_per_run(pool, ...) returns runs sorted by started_at DESC."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from _s15_db_helpers import cleanup_run, make_pool, seed_run_with_cost


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_cost_per_run_returns_recent_runs_descending():
    try:
        from app.inspector.cost import cost_per_run  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: cost_per_run must be importable ({exc})")

    pool = await make_pool()
    run_ids = []
    base = datetime.now(timezone.utc)
    try:
        async with pool.acquire() as conn:
            for offset, cost in [(2, 100), (1, 200), (0, 300)]:
                rid = await seed_run_with_cost(
                    conn,
                    cost_cents=cost,
                    started_at=base - timedelta(hours=offset),
                )
                run_ids.append(rid)

        rows = await cost_per_run(
            pool,
            limit=10,
            date_from=None,
            date_to=None,
            site_id=None,
            provider=None,
        )
        observed = [r for r in rows if getattr(r, "agent_run_id", None) in run_ids]
        assert len(observed) == 3, (
            f"AC-1: cost_per_run must return all 3 seeded runs; got {len(observed)}"
        )
        costs = [r.cost_cents for r in observed]
        assert costs == sorted(costs, reverse=True), (
            f"AC-1: cost_per_run must order by started_at DESC; got costs {costs}"
        )
    finally:
        async with pool.acquire() as conn:
            for rid in run_ids:
                await cleanup_run(conn, rid)
        await pool.close()
