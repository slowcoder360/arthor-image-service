"""s10 AC-6: pack_worker generates hero first per pack.slot_order."""

from __future__ import annotations

import os
import uuid

import pytest

from _fakes import FakeProvider
from _helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_worker_runs_hero_slot_first():
    try:
        import asyncpg
        from app.config import Settings  # type: ignore[import-not-found]
        from app.orchestration.pack_worker import run_in_background  # type: ignore[import-not-found]
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: orchestration/payload/runs/style modules must be importable ({exc})")

    raw = build_payload(num_slots=3)
    raw["pack"]["slot_order"] = ["s-0", "s-1", "s-2"]
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    fake = FakeProvider(name="openai_image", supports_pack_consistent=False)
    settings = Settings()
    services = RuntimeServices(settings=settings)
    services.pool = pool
    services.providers = {"openai_image": fake, "google_nano_banana": fake}
    services.r2 = None  # worker may short-circuit upload when r2 is None for tests
    import asyncio as _asyncio

    services.asset_pack_semaphore = _asyncio.Semaphore(4)

    run_id = await insert_pending_run(
        pool, run_type="image_pack_generation", site_id=payload.site_id
    )
    try:
        await run_in_background(services, run_id=run_id, payload=payload, style_profile=profile)
    finally:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
            )
            await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
        await pool.close()

    slot_calls = [c for c in fake.calls if c.method == "generate_single"]
    assert slot_calls, "AC-6: worker must invoke at least one generate_single call"
    assert slot_calls[0].slot_id == "s-0", (
        f"AC-6: hero slot 's-0' must be generated first; got {slot_calls[0].slot_id!r}"
    )
