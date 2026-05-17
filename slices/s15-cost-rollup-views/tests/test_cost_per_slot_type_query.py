"""s15 AC-5: cost_per_slot_type derives slot_kind by joining external_media_assets
to image_request_payloads via metadata.slot_id.
"""

from __future__ import annotations

import pytest

from _s15_db_helpers import cleanup_run, make_pool, seed_run_with_cost


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_cost_per_slot_type_derives_from_payload():
    try:
        from app.inspector.cost import cost_per_slot_type  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: cost_per_slot_type must be importable ({exc})")

    pool = await make_pool()
    run_ids = []
    try:
        async with pool.acquire() as conn:
            run_ids.append(
                await seed_run_with_cost(conn, cost_cents=100, slot_id="s-0", slot_kind="hero")
            )
            run_ids.append(
                await seed_run_with_cost(conn, cost_cents=200, slot_id="s-1", slot_kind="card")
            )
            run_ids.append(
                await seed_run_with_cost(conn, cost_cents=150, slot_id="s-2", slot_kind="hero")
            )

        rows = await cost_per_slot_type(
            pool, date_from=None, date_to=None, site_id=None, provider=None
        )
        observed = {getattr(r, "slot_kind", None): r.cost_cents for r in rows}
        assert observed.get("hero", 0) >= 250, (
            f"AC-5: hero total must include both hero rows (>=250 cents); got {observed!r}"
        )
        assert observed.get("card", 0) >= 200, (
            f"AC-5: card total must include the card row; got {observed!r}"
        )
    finally:
        async with pool.acquire() as conn:
            for rid in run_ids:
                await cleanup_run(conn, rid)
        await pool.close()
