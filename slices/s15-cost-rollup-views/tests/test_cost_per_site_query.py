"""s15 AC-1: cost_per_site groups by site_id, top-25 sorted by total descending."""

from __future__ import annotations

import uuid

import pytest

from _s15_db_helpers import cleanup_run, make_pool, seed_run_with_cost


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_cost_per_site_sorts_descending():
    try:
        from app.inspector.cost import cost_per_site  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: cost_per_site must be importable ({exc})")

    pool = await make_pool()
    run_ids = []
    site_a = uuid.uuid4()
    site_b = uuid.uuid4()
    site_c = uuid.uuid4()
    try:
        async with pool.acquire() as conn:
            run_ids.append(await seed_run_with_cost(conn, cost_cents=100, site_id=site_a))
            run_ids.append(await seed_run_with_cost(conn, cost_cents=300, site_id=site_b))
            run_ids.append(await seed_run_with_cost(conn, cost_cents=300, site_id=site_b))
            run_ids.append(await seed_run_with_cost(conn, cost_cents=50, site_id=site_c))

        rows = await cost_per_site(
            pool, limit=25, date_from=None, date_to=None, provider=None
        )
        observed = [r for r in rows if getattr(r, "site_id", None) in {site_a, site_b, site_c}]
        assert len(observed) == 3, (
            f"AC-1: cost_per_site must group by site_id; got {len(observed)} rows"
        )
        site_b_total = next(r.cost_cents for r in observed if r.site_id == site_b)
        assert site_b_total == 600, (
            f"AC-1: site_b total must be 600 cents (100+300+300=...); got {site_b_total}"
        )
        totals = [r.cost_cents for r in observed]
        assert totals == sorted(totals, reverse=True), (
            f"AC-1: cost_per_site must be sorted by total DESC; got {totals}"
        )
    finally:
        async with pool.acquire() as conn:
            for rid in run_ids:
                await cleanup_run(conn, rid)
        await pool.close()
