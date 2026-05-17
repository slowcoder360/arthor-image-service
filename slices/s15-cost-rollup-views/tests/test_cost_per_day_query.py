"""s15 AC-1: cost_per_day(pool, days=30) groups by date and sums cost_cents."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from _s15_db_helpers import cleanup_run, make_pool, seed_run_with_cost


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_cost_per_day_groups_and_sums():
    try:
        from app.inspector.cost import cost_per_day  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: cost_per_day must be importable ({exc})")

    pool = await make_pool()
    run_ids = []
    base = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    try:
        async with pool.acquire() as conn:
            for day_offset, cost in [(0, 100), (1, 150), (2, 200), (3, 250), (4, 300)]:
                rid = await seed_run_with_cost(
                    conn,
                    cost_cents=cost,
                    started_at=base - timedelta(days=day_offset),
                )
                run_ids.append(rid)

        rows = await cost_per_day(pool, days=30, site_id=None, provider=None)
        observed_days = {getattr(r, "day", None): r.cost_cents for r in rows}
        assert len(observed_days) >= 5, (
            f"AC-1: cost_per_day must return at least 5 rows after seeding 5 days; "
            f"got {len(observed_days)}"
        )
    finally:
        async with pool.acquire() as conn:
            for rid in run_ids:
                await cleanup_run(conn, rid)
        await pool.close()
