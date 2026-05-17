"""s16 AC-7: when `cold_storage_interval_seconds == 0`, `cold_storage_worker`
returns immediately without entering the loop.
"""

from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_cold_storage_worker_disabled_returns_immediately():
    try:
        from app.config import Settings  # type: ignore[import-not-found]
        from app.jobs.cold_storage import cold_storage_worker  # type: ignore[import-not-found]
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-7: cold_storage_worker + Settings + RuntimeServices must be importable ({exc})"
        )

    services = RuntimeServices(settings=Settings(cold_storage_interval_seconds=0))

    try:
        await asyncio.wait_for(cold_storage_worker(services), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail(
            "AC-7: cold_storage_worker must exit immediately when "
            "settings.cold_storage_interval_seconds == 0"
        )
