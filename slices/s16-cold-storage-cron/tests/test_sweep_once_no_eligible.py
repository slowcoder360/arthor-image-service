"""s16 AC-2: empty DB → sweep_once returns 0; no R2 calls were issued."""

from __future__ import annotations

import os

import pytest

from _s16_helpers import FakeR2Client, make_pool


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_sweep_once_returns_zero_when_no_eligible_rows():
    try:
        from app.jobs.cold_storage import sweep_once  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: sweep_once must be importable ({exc})")

    pool = await make_pool()
    r2 = FakeR2Client()
    try:
        result = await sweep_once(pool, r2)
        assert result == 0, (
            f"AC-2: sweep_once with no eligible rows must return 0; got {result!r}"
        )
        assert r2.moves == [], (
            f"AC-2: sweep_once with no eligible rows must NOT call R2; got {r2.moves!r}"
        )
    finally:
        await pool.close()
