"""s10 AC-8: ProviderError on batch → falls back to per-slot generate_single with reference."""

from __future__ import annotations

import asyncio
import os

import pytest

from _fakes import FakeProvider
from _helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_batch_failure_falls_back_to_per_slot_generation():
    try:
        import asyncpg
        from app.config import Settings  # type: ignore[import-not-found]
        from app.orchestration.pack_worker import run_in_background  # type: ignore[import-not-found]
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-8: dependencies must be importable ({exc})")

    raw = build_payload(num_slots=3)
    raw["pack"]["default_provider_hint"] = "google_nano_banana"
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    nano = FakeProvider(
        name="google_nano_banana",
        supports_pack_consistent=True,
        pack_failure=True,
    )
    services = RuntimeServices(settings=Settings())
    services.pool = pool
    services.providers = {"openai_image": nano, "google_nano_banana": nano}
    services.asset_pack_semaphore = asyncio.Semaphore(4)

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

    batch_calls = [c for c in nano.calls if c.method == "generate_pack_consistent"]
    fallback_singles = [
        c
        for c in nano.calls
        if c.method == "generate_single" and c.slot_id and c.slot_id != "s-0"
    ]
    assert batch_calls, "AC-8: batch path must have been attempted first"
    assert fallback_singles, (
        "AC-8: after ProviderError on batch, worker must fall back to generate_single for each non-hero slot"
    )
