"""s16 AC-3: `uploaded` rows are NEVER moved, regardless of age."""

from __future__ import annotations

import pytest

from _s16_helpers import FakeR2Client, cleanup_asset, insert_asset, make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_sweep_once_never_moves_uploaded_rows():
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
                conn, status="uploaded", age_days=400, r2_key="warm/active.png"
            )
        result = await sweep_once(pool, r2)
        assert result == 0, (
            f"AC-3: uploaded rows must never be moved regardless of age; got {result!r}"
        )
        assert r2.moves == [], (
            f"AC-3: R2 must not be called for uploaded rows; got {r2.moves!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if asset_id is not None:
                await cleanup_asset(conn, asset_id)
        await pool.close()
