"""Shared DB + asset helpers for s14 inspector-iteration tests."""

from __future__ import annotations

import json
import os
import uuid

import pytest


async def make_pool():
    try:
        import asyncpg
    except ImportError as exc:
        pytest.fail(f"asyncpg is not installed: {exc}")
    return await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)


async def seed_uploaded_asset(
    conn,
    *,
    run_id: uuid.UUID | None = None,
    asset_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    slot_id: str = "s-0",
    seed: int = 100,
    prompt_hash: str = "h0",
    run_type: str = "image_pack_generation",
) -> tuple[uuid.UUID, uuid.UUID]:
    run_id = run_id or uuid.uuid4()
    asset_id = asset_id or uuid.uuid4()
    site_id = site_id or uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO agent_runs (id, run_type, status, site_id, metadata, cost_cents)
        VALUES ($1, $2, 'complete', $3, $4::jsonb, 1)
        """,
        run_id,
        run_type,
        site_id,
        json.dumps({"site_id": str(site_id), "style_profile": {}}),
    )
    await conn.execute(
        """
        INSERT INTO external_media_assets
          (id, provider, status, agent_run_id, site_id, metadata, r2_url)
        VALUES ($1, 'openai_image', 'uploaded', $2, $3, $4::jsonb, $5)
        """,
        asset_id,
        run_id,
        site_id,
        json.dumps({"slot_id": slot_id, "seed": seed, "prompt_hash": prompt_hash}),
        f"https://r2.example.com/{asset_id}.png",
    )
    await conn.execute(
        """
        INSERT INTO tool_calls
          (id, run_id, provider, model_version, status, cost_cents, latency_ms)
        VALUES ($1, $2, 'openai_image', 'gpt-image-1', 'ok', 12, 900)
        """,
        uuid.uuid4(),
        run_id,
    )
    return run_id, asset_id


async def supersede_asset_row(
    conn,
    *,
    old_asset_id: uuid.UUID,
    new_asset_id: uuid.UUID,
    new_run_id: uuid.UUID,
    site_id: uuid.UUID,
    slot_id: str = "s-0",
) -> None:
    await conn.execute(
        """
        INSERT INTO agent_runs (id, run_type, status, parent_run_id, site_id, metadata, cost_cents)
        VALUES ($1, 'image_slot_regenerate', 'complete', NULL, $2, '{}'::jsonb, 1)
        """,
        new_run_id,
        site_id,
    )
    await conn.execute(
        """
        INSERT INTO external_media_assets
          (id, provider, status, agent_run_id, site_id, metadata, r2_url)
        VALUES ($1, 'openai_image', 'uploaded', $2, $3, $4::jsonb, $5)
        """,
        new_asset_id,
        new_run_id,
        site_id,
        json.dumps({"slot_id": slot_id, "seed": 200, "prompt_hash": "h1"}),
        f"https://r2.example.com/{new_asset_id}.png",
    )
    await conn.execute(
        """
        UPDATE external_media_assets
        SET status = 'superseded',
            metadata = metadata || jsonb_build_object('replaced_by', $2::text)
        WHERE id = $1
        """,
        old_asset_id,
        str(new_asset_id),
    )


async def cleanup_run(conn, run_id: uuid.UUID) -> None:
    await conn.execute(
        "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
    )
    await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
    await conn.execute(
        "DELETE FROM image_request_payloads WHERE agent_run_id = $1", run_id
    )
    await conn.execute(
        "DELETE FROM agent_runs WHERE parent_run_id = $1", run_id
    )
    await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
