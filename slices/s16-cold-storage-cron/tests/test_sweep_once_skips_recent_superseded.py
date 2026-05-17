"""s16 AC-3: superseded rows newer than 30 days are NOT moved."""

from __future__ import annotations

import pytest

from _s16_helpers import FakeR2Client, cleanup_asset, insert_asset, make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_sweep_once_skips_recent_superseded_rows():
    try:
        from app.jobs.cold_storage import sweep_once  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: sweep_once must be importable ({exc})")

    pool = await make_pool()
    r2 = FakeR2Client()
    asset_id = None
    try:
        async with pool.acquire() as conn:
            asset_id = await insert_asset(
                conn, status="superseded", age_days=5, r2_key="warm/recent.png"
            )
        result = await sweep_once(pool, r2)
        assert result == 0, (
            f"AC-3: superseded rows < 30 days old must be skipped; got moved {result!r}"
        )
        assert r2.moves == [], (
            f"AC-3: R2 must not be called for recent superseded rows; got {r2.moves!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if asset_id is not None:
                await cleanup_asset(conn, asset_id)
        await pool.close()
