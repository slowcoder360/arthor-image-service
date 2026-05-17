"""s16 AC-4: after a successful sweep, `r2_url` is cleared (NULL) because the
public URL is no longer valid post-rotation.
"""

from __future__ import annotations

import pytest

from _s16_helpers import FakeR2Client, cleanup_asset, insert_asset, make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_sweep_clears_r2_url_after_move():
    try:
        from app.jobs.cold_storage import sweep_once  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: sweep_once must be importable ({exc})")

    pool = await make_pool()
    r2 = FakeR2Client()
    asset_id = None
    try:
        async with pool.acquire() as conn:
            asset_id = await insert_asset(
                conn,
                status="superseded",
                age_days=60,
                r2_key="warm/clearme.png",
                r2_url="https://r2.example.com/clearme.png",
            )
        moved = await sweep_once(pool, r2)
        assert moved == 1, f"AC-4: must move the eligible row; got {moved!r}"
        async with pool.acquire() as conn:
            r2_url = await conn.fetchval(
                "SELECT r2_url FROM external_media_assets WHERE id = $1", asset_id
            )
        assert r2_url is None, (
            f"AC-4: r2_url must be NULL after the move; got {r2_url!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if asset_id is not None:
                await cleanup_asset(conn, asset_id)
        await pool.close()
