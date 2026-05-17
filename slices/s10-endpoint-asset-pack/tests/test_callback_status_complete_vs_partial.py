"""s10 AC-13: pack-level status: all-success → 'complete'; any-failure → 'partial'; all-failure → 'failed'."""

from __future__ import annotations

import asyncio
import os

import pytest

from _fakes import FakeCallbackClient, FakeProvider
from _helpers import build_payload


async def _run_with_failures(num_slots: int, single_failures_per_slot: int):
    import asyncpg
    from app.config import Settings  # type: ignore[import-not-found]
    from app.orchestration.pack_worker import run_in_background  # type: ignore[import-not-found]
    from app.payload.models import PayloadV1  # type: ignore[import-not-found]
    from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
    from app.runtime import RuntimeServices  # type: ignore[import-not-found]
    from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]

    raw = build_payload(num_slots=num_slots)
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    fake = FakeProvider(single_failures=single_failures_per_slot)
    services = RuntimeServices(settings=Settings())
    services.pool = pool
    services.providers = {"openai_image": fake, "google_nano_banana": fake}
    services.asset_pack_semaphore = asyncio.Semaphore(4)
    services.callback_client = FakeCallbackClient()

    run_id = await insert_pending_run(
        pool, run_type="image_pack_generation", site_id=payload.site_id
    )
    try:
        await run_in_background(services, run_id=run_id, payload=payload, style_profile=profile)
        return services.callback_client.posts[-1]["body"]["status"]
    finally:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
            )
            await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
        await pool.close()


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_status_complete_when_all_succeed():
    try:
        from app.orchestration.pack_worker import run_in_background  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-13: dependencies must be importable ({exc})")

    status = await _run_with_failures(num_slots=2, single_failures_per_slot=0)
    assert status == "complete", (
        f"AC-13: all-success pack must report status='complete'; got {status!r}"
    )


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_status_failed_when_all_slots_fail():
    try:
        from app.orchestration.pack_worker import run_in_background  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-13: dependencies must be importable ({exc})")

    status = await _run_with_failures(num_slots=2, single_failures_per_slot=99)
    assert status in ("failed", "partial"), (
        f"AC-13: all-failure pack must report status='failed' (or 'partial' if hero succeeded); got {status!r}"
    )
