"""s11 AC-7: when the provider fails, the new asset is `failed` and the old
asset stays `uploaded` (no supersession on failure).
"""

from __future__ import annotations

import os

import pytest

from _s11_fakes import FakeProvider
from _s11_helpers import build_payload, cleanup_run, seed_prior_pack_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_regenerate_failure_leaves_old_asset_uploaded():
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
        pytest.fail(f"AC-7: orchestration deps must be importable ({exc})")

    raw = build_payload(num_slots=2)
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)
    slot = payload.slots[0]

    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    fake = FakeProvider(name="openai_image", single_failures=2)
    services = RuntimeServices(settings=Settings())
    services.pool = pool
    services.providers = {"openai_image": fake, "google_nano_banana": fake}

    new_run_id = None
    old_run_id = None
    old_asset_id = None
    try:
        async with pool.acquire() as conn:
            old_run_id, old_asset_id = await seed_prior_pack_run(conn, raw, slot_id=slot.slot_id)

        new_run_id = await insert_pending_run(
            pool, run_type="image_slot_regenerate", site_id=payload.site_id
        )
        try:
            await run_single_slot_in_background(
                services,
                new_run_id=new_run_id,
                slot=slot,
                style_profile=profile,
                seed=101,
                prompt_modifier_text=None,
                old_asset_id=old_asset_id,
            )
        except Exception:
            pass

        async with pool.acquire() as conn:
            old_row = await conn.fetchrow(
                "SELECT status FROM external_media_assets WHERE id = $1",
                old_asset_id,
            )
            new_row = await conn.fetchrow(
                """
                SELECT status FROM external_media_assets
                WHERE agent_run_id = $1
                """,
                new_run_id,
            )
        assert old_row is not None and old_row["status"] == "uploaded", (
            f"AC-7: old asset must remain 'uploaded' on regenerate failure; "
            f"got status={old_row and old_row['status']!r}"
        )
        assert new_row is not None and new_row["status"] == "failed", (
            f"AC-7: new asset must be 'failed' on provider failure; "
            f"got status={new_row and new_row['status']!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if new_run_id is not None:
                await cleanup_run(conn, new_run_id)
            if old_run_id is not None:
                await cleanup_run(conn, old_run_id)
        await pool.close()
