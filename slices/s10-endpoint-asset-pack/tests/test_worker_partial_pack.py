"""s10 AC-11: provider fails both attempts for one slot → that asset is 'failed'; pack status='partial'."""

from __future__ import annotations

import asyncio
import os

import pytest

from _fakes import FakeCallbackClient, FakeProvider
from _helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_one_slot_failure_yields_partial_pack_status():
    try:
        import asyncpg
        from app.config import Settings  # type: ignore[import-not-found]
        from app.orchestration.pack_worker import run_in_background  # type: ignore[import-not-found]
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-11: dependencies must be importable ({exc})")

    raw = build_payload(num_slots=2)
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    fake = FakeProvider(single_failures=99)
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

        posts = getattr(services, "callback_client", None)
        assert posts and posts.posts, (
            "AC-11/AC-13: callback must be POSTed at run completion"
        )
        body = posts.posts[-1]["body"]
        assert body.get("status") in ("partial", "failed"), (
            f"AC-11: with all slots failing, pack status must be 'partial' or 'failed'; got {body.get('status')!r}"
        )
    finally:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
            )
            await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
        await pool.close()
