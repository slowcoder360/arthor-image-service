"""s11 AC-5: `new_prompt_modifier` overlays onto slot.intent before
`build_slot_prompt` runs, so the resolved prompt text contains the modifier
and the new prompt_hash differs from the original.
"""

from __future__ import annotations

import os

import pytest

from _s11_fakes import FakeProvider
from _s11_helpers import build_payload, cleanup_run, seed_prior_pack_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_regenerate_prompt_modifier_appears_in_prompt_and_changes_hash():
    try:
        import asyncpg
        from app.config import Settings  # type: ignore[import-not-found]
        from app.orchestration.pack_worker import (  # type: ignore[import-not-found]
            run_single_slot_in_background,
        )
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.runs.agent_runs import insert_pending_run  # type: ignore[import-not-found]
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: orchestration deps must be importable ({exc})")

    raw = build_payload(num_slots=2)
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)
    slot = payload.slots[0]
    original_prompt_hash = "deadbeef00"
    modifier = "with neon accents under blue dusk light"

    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    fake = FakeProvider(name="openai_image")
    services = RuntimeServices(settings=Settings())
    services.pool = pool
    services.providers = {"openai_image": fake, "google_nano_banana": fake}

    new_run_id = None
    old_run_id = None
    try:
        async with pool.acquire() as conn:
            old_run_id, old_asset_id = await seed_prior_pack_run(
                conn,
                raw,
                slot_id=slot.slot_id,
                prompt_hash=original_prompt_hash,
            )

        new_run_id = await insert_pending_run(
            pool, run_type="image_slot_regenerate", site_id=payload.site_id
        )
        await run_single_slot_in_background(
            services,
            new_run_id=new_run_id,
            slot=slot,
            style_profile=profile,
            seed=101,
            prompt_modifier_text=modifier,
            old_asset_id=old_asset_id,
        )

        assert fake.calls, "AC-5: provider must have been called once"
        assert "neon" in (fake.calls[0].prompt or "").lower(), (
            f"AC-5: resolved prompt must contain the modifier text 'neon'; "
            f"got prompt={fake.calls[0].prompt!r}"
        )

        import json as _json
        async with pool.acquire() as conn:
            new_meta = await conn.fetchval(
                """
                SELECT metadata FROM external_media_assets
                WHERE agent_run_id = $1
                """,
                new_run_id,
            )
        if isinstance(new_meta, str):
            new_meta = _json.loads(new_meta)
        new_hash = new_meta and new_meta.get("prompt_hash")
        assert new_hash and new_hash != original_prompt_hash, (
            f"AC-5: new asset prompt_hash must differ from the original "
            f"({original_prompt_hash!r}); got {new_hash!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if new_run_id is not None:
                await cleanup_run(conn, new_run_id)
            if old_run_id is not None:
                await cleanup_run(conn, old_run_id)
        await pool.close()
