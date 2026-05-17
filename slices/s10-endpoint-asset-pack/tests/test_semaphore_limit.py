"""s10 AC-5 / ADR-0008: max_concurrent_packs=2 → only 2 concurrent runs in flight at any time."""

from __future__ import annotations

import asyncio
import os

import pytest

from _fakes import FakeProvider
from _helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_semaphore_caps_concurrent_packs():
    try:
        import asyncpg
        from app.config import Settings  # type: ignore[import-not-found]
        from app.orchestration.pack_worker import run_in_background  # type: ignore[import-not-found]
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: dependencies must be importable ({exc})")

    in_flight = 0
    max_observed = 0

    class GatedProvider(FakeProvider):
        async def generate_single(self, **kwargs):
            nonlocal in_flight, max_observed
            in_flight += 1
            max_observed = max(max_observed, in_flight)
            await asyncio.sleep(0.01)
            in_flight -= 1
            return await super().generate_single(**kwargs)

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=4)
    services = RuntimeServices(settings=Settings())
    services.pool = pool
    fake = GatedProvider()
    services.providers = {"openai_image": fake, "google_nano_banana": fake}
    services.asset_pack_semaphore = asyncio.Semaphore(2)

    payloads = [build_payload(num_slots=2) for _ in range(5)]
    run_ids = []
    try:
        tasks = []
        for raw in payloads:
            payload = PayloadV1.model_validate(raw)
            profile = await resolve_style_profile(payload)
            run_id = await insert_pending_run(
                pool, run_type="image_pack_generation", site_id=payload.site_id
            )
            run_ids.append(run_id)
            tasks.append(
                run_in_background(
                    services, run_id=run_id, payload=payload, style_profile=profile
                )
            )
        await asyncio.gather(*tasks)

        assert max_observed <= 2, (
            f"AC-5: with semaphore=2, no more than 2 packs may run in parallel; observed max {max_observed}"
        )
    finally:
        async with pool.acquire() as conn:
            for rid in run_ids:
                await conn.execute(
                    "DELETE FROM external_media_assets WHERE agent_run_id = $1", rid
                )
                await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", rid)
                await conn.execute("DELETE FROM agent_runs WHERE id = $1", rid)
        await pool.close()
