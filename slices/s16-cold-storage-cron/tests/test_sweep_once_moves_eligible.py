"""s16 AC-3 + AC-4: three superseded rows older than 30 days → sweep_once
returns 3; mocked R2 receives three move calls; rows updated with `cold/` prefix.
"""

from __future__ import annotations

import os

import pytest

from _s16_helpers import FakeR2Client, cleanup_asset, insert_asset, make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_sweep_once_moves_eligible_rows():
    try:
        from app.jobs.cold_storage import sweep_once  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: sweep_once must be importable ({exc})")

    pool = await make_pool()
    r2 = FakeR2Client()
    seeded = []
    try:
        async with pool.acquire() as conn:
            for i in range(3):
                aid = await insert_asset(
                    conn,
                    status="superseded",
                    age_days=45,
                    r2_key=f"warm/old-{i}.png",
                )
                seeded.append(aid)

        result = await sweep_once(pool, r2)
        assert result == 3, (
            f"AC-3: sweep_once must return 3 (moved count); got {result!r}"
        )
        assert len(r2.moves) == 3, (
            f"AC-4: R2 must receive 3 move calls; got {len(r2.moves)}"
        )

        async with pool.acquire() as conn:
            for aid in seeded:
                r2_key = await conn.fetchval(
                    "SELECT r2_key FROM external_media_assets WHERE id = $1", aid
                )
                assert r2_key and r2_key.startswith("cold/"), (
                    f"AC-4: post-sweep r2_key must begin with 'cold/'; got {r2_key!r}"
                )
    finally:
        async with pool.acquire() as conn:
            for aid in seeded:
                await cleanup_asset(conn, aid)
        await pool.close()
