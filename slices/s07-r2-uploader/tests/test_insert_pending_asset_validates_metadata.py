"""s07 AC-5: insert_pending_asset validates ADR-0005 metadata keys; persists with status='pending'."""

from __future__ import annotations

import os
import uuid

import pytest


REQUIRED_METADATA_KEYS = {
    "slot_id",
    "slot_intent",
    "style_profile_id",
    "prompt_hash",
    "seed",
    "determinism_level",
    "run_id",
}


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_insert_pending_asset_rejects_missing_metadata_key():
    try:
        import asyncpg
        from app.storage.asset_writer import (  # type: ignore[import-not-found]
            insert_pending_asset,
        )
    except ImportError as exc:
        pytest.fail(f"AC-5: insert_pending_asset must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        partial = {
            "slot_id": "s-hero",
            "slot_intent": "establish brand mood",
            "style_profile_id": str(uuid.uuid4()),
        }
        agent_run_id = uuid.uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')",
                agent_run_id,
            )

        with pytest.raises(ValueError):
            await insert_pending_asset(
                pool,
                agent_run_id=agent_run_id,
                site_id=uuid.uuid4(),
                provider="openai_image",
                model_version="gpt-image-1",
                metadata=partial,
            )

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", agent_run_id)
    finally:
        await pool.close()


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_insert_pending_asset_writes_pending_row():
    try:
        import asyncpg
        from app.storage.asset_writer import (  # type: ignore[import-not-found]
            insert_pending_asset,
        )
    except ImportError as exc:
        pytest.fail(f"AC-5: insert_pending_asset must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        agent_run_id = uuid.uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')",
                agent_run_id,
            )

        complete = {
            "slot_id": "s-hero",
            "slot_intent": "establish brand mood",
            "style_profile_id": str(uuid.uuid4()),
            "prompt_hash": "hash-1",
            "seed": 42,
            "determinism_level": "best-effort",
            "run_id": str(uuid.uuid4()),
        }
        asset_id = await insert_pending_asset(
            pool,
            agent_run_id=agent_run_id,
            site_id=uuid.uuid4(),
            provider="openai_image",
            model_version="gpt-image-1",
            metadata=complete,
        )
        assert isinstance(asset_id, uuid.UUID), "AC-5: asset_id must be a UUID"
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM external_media_assets WHERE id = $1", asset_id
            )
        assert row["status"] == "pending", (
            f"AC-5: row must be inserted with status='pending'; got {row['status']!r}"
        )

        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM external_media_assets WHERE id = $1", asset_id
            )
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", agent_run_id)
    finally:
        await pool.close()
