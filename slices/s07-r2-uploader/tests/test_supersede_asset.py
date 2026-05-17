"""s07 AC-7: supersede_asset transitions uploaded → superseded; sets metadata.replaced_by atomically."""

from __future__ import annotations

import os
import uuid

import pytest


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_supersede_asset_transitions_and_sets_replaced_by():
    try:
        import asyncpg
        from app.storage.asset_writer import (  # type: ignore[import-not-found]
            insert_pending_asset,
            mark_asset_generated,
            mark_asset_uploaded,
        )
        from app.storage.supersession import supersede_asset  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-7: supersession + writers must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        agent_run_id = uuid.uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')",
                agent_run_id,
            )

        async def _upload_one() -> uuid.UUID:
            meta = {
                "slot_id": "s",
                "slot_intent": "intent",
                "style_profile_id": str(uuid.uuid4()),
                "prompt_hash": "h",
                "seed": 1,
                "determinism_level": "best-effort",
                "run_id": str(uuid.uuid4()),
            }
            aid = await insert_pending_asset(
                pool,
                agent_run_id=agent_run_id,
                site_id=uuid.uuid4(),
                provider="openai_image",
                model_version="gpt-image-1",
                metadata=meta,
            )
            await mark_asset_generated(
                pool, aid, width=1, height=1, bytes_len=1, external_id="ext"
            )
            await mark_asset_uploaded(pool, aid, r2_key="k", r2_url="https://x")
            return aid

        old = await _upload_one()
        new = await _upload_one()
        await supersede_asset(pool, old_asset_id=old, new_asset_id=new)

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status, metadata FROM external_media_assets WHERE id = $1", old
            )
        assert row["status"] == "superseded", (
            "AC-7: old asset must transition to 'superseded'"
        )
        import json

        meta = (
            row["metadata"]
            if isinstance(row["metadata"], dict)
            else json.loads(row["metadata"])
        )
        assert str(meta.get("replaced_by")) == str(new), (
            f"AC-7: metadata.replaced_by must equal new_asset_id; got {meta.get('replaced_by')!r}"
        )

        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM external_media_assets WHERE id = ANY($1::uuid[])",
                [old, new],
            )
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", agent_run_id)
    finally:
        await pool.close()


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_supersede_asset_on_non_uploaded_raises_invalid_state_transition():
    try:
        import asyncpg
        from app.storage.asset_writer import (  # type: ignore[import-not-found]
            InvalidStateTransition,
            insert_pending_asset,
        )
        from app.storage.supersession import supersede_asset  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-7: supersession + writers must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        agent_run_id = uuid.uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')",
                agent_run_id,
            )

        meta = {
            "slot_id": "s",
            "slot_intent": "intent",
            "style_profile_id": str(uuid.uuid4()),
            "prompt_hash": "h",
            "seed": 1,
            "determinism_level": "best-effort",
            "run_id": str(uuid.uuid4()),
        }
        old = await insert_pending_asset(
            pool,
            agent_run_id=agent_run_id,
            site_id=uuid.uuid4(),
            provider="openai_image",
            model_version="gpt-image-1",
            metadata=meta,
        )
        with pytest.raises(InvalidStateTransition):
            await supersede_asset(pool, old_asset_id=old, new_asset_id=uuid.uuid4())

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM external_media_assets WHERE id = $1", old)
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", agent_run_id)
    finally:
        await pool.close()
