"""s11 AC-7: after the background task finishes, the old asset is `superseded`
with `metadata.replaced_by = new_asset_id`; the new asset is `uploaded`.

Exercises the worker function directly (`run_single_slot_in_background`) with
a FakeProvider so the supersession transition is deterministic and observable.
"""

from __future__ import annotations

import os
import uuid

import pytest

from _s11_fakes import FakeProvider
from _s11_helpers import build_payload, cleanup_run, seed_prior_pack_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_regenerate_happy_path_supersedes_old_asset():
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
        pytest.fail(
            f"AC-7: pack_worker.run_single_slot_in_background + payload + runs + style "
            f"must be importable ({exc})"
        )

    raw = build_payload(num_slots=2)
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)
    slot = payload.slots[0]

    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    fake = FakeProvider(name="openai_image")
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
            pool,
            run_type="image_slot_regenerate",
            site_id=payload.site_id,
        )
        await run_single_slot_in_background(
            services,
            new_run_id=new_run_id,
            slot=slot,
            style_profile=profile,
            seed=101,
            prompt_modifier_text=None,
            old_asset_id=old_asset_id,
        )

        async with pool.acquire() as conn:
            old_row = await conn.fetchrow(
                "SELECT status, metadata FROM external_media_assets WHERE id = $1",
                old_asset_id,
            )
            new_row = await conn.fetchrow(
                """
                SELECT id, status FROM external_media_assets
                WHERE agent_run_id = $1
                """,
                new_run_id,
            )

        assert old_row is not None and old_row["status"] == "superseded", (
            f"AC-7: old asset must transition to 'superseded' after a successful regenerate; "
            f"got status={old_row and old_row['status']!r}"
        )
        import json as _json
        old_meta = old_row["metadata"]
        if isinstance(old_meta, str):
            old_meta = _json.loads(old_meta)
        assert new_row is not None and new_row["status"] == "uploaded", (
            f"AC-7: new asset must end as 'uploaded'; got "
            f"status={new_row and new_row['status']!r}"
        )
        assert str(old_meta.get("replaced_by")) == str(new_row["id"]), (
            f"AC-7: old asset metadata.replaced_by must point to the new asset id; "
            f"got {old_meta.get('replaced_by')!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if new_run_id is not None:
                await cleanup_run(conn, new_run_id)
            if old_run_id is not None:
                await cleanup_run(conn, old_run_id)
        await pool.close()
