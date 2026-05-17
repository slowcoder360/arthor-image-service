"""s07 AC-6: state-machine transitions per ADR-0005; bad transitions raise InvalidStateTransition."""

from __future__ import annotations

import os
import uuid

import pytest


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_happy_path_pending_generated_uploaded():
    try:
        import asyncpg
        from app.storage.asset_writer import (  # type: ignore[import-not-found]
            insert_pending_asset,
            mark_asset_generated,
            mark_asset_uploaded,
        )
    except ImportError as exc:
        pytest.fail(f"AC-6: state-machine writers must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        agent_run_id = uuid.uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')",
                agent_run_id,
            )

        complete_meta = {
            "slot_id": "s",
            "slot_intent": "intent",
            "style_profile_id": str(uuid.uuid4()),
            "prompt_hash": "h",
            "seed": 1,
            "determinism_level": "best-effort",
            "run_id": str(uuid.uuid4()),
        }
        asset_id = await insert_pending_asset(
            pool,
            agent_run_id=agent_run_id,
            site_id=uuid.uuid4(),
            provider="openai_image",
            model_version="gpt-image-1",
            metadata=complete_meta,
        )
        await mark_asset_generated(
            pool,
            asset_id,
            width=1920,
            height=1080,
            bytes_len=2048,
            external_id="img-x",
        )
        await mark_asset_uploaded(
            pool, asset_id, r2_key="arthor-image-service/x/y.png", r2_url="https://x"
        )

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM external_media_assets WHERE id = $1", asset_id
            )
        assert row["status"] == "uploaded", (
            f"AC-6: happy path must terminate at status='uploaded'; got {row['status']!r}"
        )

        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM external_media_assets WHERE id = $1", asset_id
            )
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", agent_run_id)
    finally:
        await pool.close()


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_mark_uploaded_from_failed_raises_invalid_state_transition():
    try:
        import asyncpg
        from app.storage.asset_writer import (  # type: ignore[import-not-found]
            InvalidStateTransition,
            insert_pending_asset,
            mark_asset_failed,
            mark_asset_uploaded,
        )
    except ImportError as exc:
        pytest.fail(f"AC-6: state-machine writers must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        agent_run_id = uuid.uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')",
                agent_run_id,
            )

        complete_meta = {
            "slot_id": "s",
            "slot_intent": "intent",
            "style_profile_id": str(uuid.uuid4()),
            "prompt_hash": "h",
            "seed": 1,
            "determinism_level": "best-effort",
            "run_id": str(uuid.uuid4()),
        }
        asset_id = await insert_pending_asset(
            pool,
            agent_run_id=agent_run_id,
            site_id=uuid.uuid4(),
            provider="openai_image",
            model_version="gpt-image-1",
            metadata=complete_meta,
        )
        await mark_asset_failed(pool, asset_id, error="boom")

        with pytest.raises(InvalidStateTransition):
            await mark_asset_uploaded(
                pool, asset_id, r2_key="x", r2_url="https://x"
            )

        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM external_media_assets WHERE id = $1", asset_id
            )
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", agent_run_id)
    finally:
        await pool.close()
