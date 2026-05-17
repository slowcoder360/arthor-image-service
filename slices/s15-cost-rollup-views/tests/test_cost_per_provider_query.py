"""s15 AC-1: cost_per_provider groups by tool_calls.provider with correct totals."""

from __future__ import annotations

import pytest

from _s15_db_helpers import cleanup_run, make_pool, seed_run_with_cost


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_cost_per_provider_totals():
    try:
        from app.inspector.cost import cost_per_provider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: cost_per_provider must be importable ({exc})")

    pool = await make_pool()
    run_ids = []
    try:
        async with pool.acquire() as conn:
            run_ids.append(
                await seed_run_with_cost(conn, cost_cents=400, provider="openai_image")
            )
            run_ids.append(
                await seed_run_with_cost(conn, cost_cents=600, provider="openai_image")
            )
            run_ids.append(
                await seed_run_with_cost(conn, cost_cents=300, provider="google_nano_banana")
            )

        rows = await cost_per_provider(
            pool, date_from=None, date_to=None, site_id=None
        )
        observed = {getattr(r, "provider", None): r.cost_cents for r in rows}
        assert observed.get("openai_image", 0) >= 1000, (
            f"AC-1: openai_image total must be at least 1000 cents; got {observed!r}"
        )
        assert observed.get("google_nano_banana", 0) >= 300, (
            f"AC-1: google_nano_banana total must be at least 300 cents; got {observed!r}"
        )
    finally:
        async with pool.acquire() as conn:
            for rid in run_ids:
                await cleanup_run(conn, rid)
        await pool.close()
