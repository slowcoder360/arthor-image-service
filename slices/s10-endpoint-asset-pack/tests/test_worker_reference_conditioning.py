"""s10 AC-6: non-hero slots receive reference_images=[hero_bytes] when provider supports it."""

from __future__ import annotations

import asyncio
import os

import pytest

from _fakes import FakeProvider
from _helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_non_hero_slots_receive_hero_reference():
    try:
        import asyncpg
        from app.config import Settings  # type: ignore[import-not-found]
        from app.orchestration.pack_worker import run_in_background  # type: ignore[import-not-found]
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: dependencies must be importable ({exc})")

    raw = build_payload(num_slots=3)
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    fake = FakeProvider(supports_pack_consistent=False, supports_reference_image=True)
    services = RuntimeServices(settings=Settings())
    services.pool = pool
    services.providers = {"openai_image": fake, "google_nano_banana": fake}
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

    single_calls = [c for c in fake.calls if c.method == "generate_single"]
    assert single_calls, "AC-6: worker must invoke generate_single calls"
    hero_call = next((c for c in single_calls if c.slot_id == "s-0"), None)
    assert hero_call is not None and hero_call.has_reference is False, (
        "AC-6: hero call must be made WITHOUT a reference image (it IS the reference)"
    )
    non_hero_with_ref = [
        c for c in single_calls if c.slot_id and c.slot_id != "s-0" and c.has_reference
    ]
    assert non_hero_with_ref, (
        "AC-6: non-hero slots conditioned on the hero must receive reference_images=[hero_bytes]"
    )
