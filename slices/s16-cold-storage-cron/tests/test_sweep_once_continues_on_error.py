"""s16 AC-1: per-row try/except — when one row's R2 move fails, the worker
keeps going with the next; return value counts only the successes.
"""

from __future__ import annotations

import pytest

from _s16_helpers import FakeR2Client, cleanup_asset, insert_asset, make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_sweep_once_continues_after_per_row_error():
    try:
        from app.jobs.cold_storage import sweep_once  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: sweep_once must be importable ({exc})")

    pool = await make_pool()
    seeded = []
    bad_key = "warm/middle.png"
    r2 = FakeR2Client(fail_on={bad_key})
    try:
        async with pool.acquire() as conn:
            seeded.append(
                await insert_asset(
                    conn, status="superseded", age_days=45, r2_key="warm/first.png"
                )
            )
            seeded.append(
                await insert_asset(
                    conn, status="superseded", age_days=45, r2_key=bad_key
                )
            )
            seeded.append(
                await insert_asset(
                    conn, status="superseded", age_days=45, r2_key="warm/third.png"
                )
            )
        result = await sweep_once(pool, r2)
        assert result == 2, (
            f"AC-1: returned count must reflect only successes (2); got {result!r}"
        )
        moved_keys = {src for src, dst in r2.moves}
        assert "warm/first.png" in moved_keys and "warm/third.png" in moved_keys, (
            f"AC-1: first and third rows must still be processed when middle row fails; "
            f"got moved keys {moved_keys!r}"
        )
    finally:
        async with pool.acquire() as conn:
            for aid in seeded:
                await cleanup_asset(conn, aid)
        await pool.close()
