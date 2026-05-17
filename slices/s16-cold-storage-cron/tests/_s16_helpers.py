"""Shared helpers for s16 cold-storage tests: DB seeding + a fake R2 client
that records copy + delete calls.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest


async def make_pool():
    try:
        import asyncpg
    except ImportError as exc:
        pytest.fail(f"asyncpg is not installed: {exc}")
    return await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)


async def insert_asset(
    conn,
    *,
    status: str,
    age_days: int,
    r2_key: str,
    r2_url: str | None = "https://r2.example.com/asset.png",
) -> uuid.UUID:
    """Insert an external_media_assets row with controlled updated_at age."""
    run_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    site_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO agent_runs (id, run_type, status, site_id, metadata, cost_cents)
        VALUES ($1, 'image_pack_generation', 'complete', $2, '{}'::jsonb, 1)
        """,
        run_id,
        site_id,
    )
    backdated = datetime.now(timezone.utc) - timedelta(days=age_days)
    await conn.execute(
        """
        INSERT INTO external_media_assets
          (id, provider, status, agent_run_id, site_id, metadata, r2_key, r2_url,
           created_at, updated_at)
        VALUES ($1, 'openai_image', $2, $3, $4, '{}'::jsonb, $5, $6, $7, $7)
        """,
        asset_id,
        status,
        run_id,
        site_id,
        r2_key,
        r2_url,
        backdated,
    )
    return asset_id


async def cleanup_asset(conn, asset_id: uuid.UUID) -> None:
    run_id = await conn.fetchval(
        "SELECT agent_run_id FROM external_media_assets WHERE id = $1", asset_id
    )
    await conn.execute("DELETE FROM external_media_assets WHERE id = $1", asset_id)
    if run_id is not None:
        await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)


class FakeR2Client:
    """Records every move_to_cold_storage call. Optionally fails on specific src_keys."""

    def __init__(self, fail_on: set[str] | None = None):
        self.moves: list[tuple[str, str]] = []
        self.fail_on = fail_on or set()

    async def move_to_cold_storage(self, *, src_key: str) -> str:
        if src_key in self.fail_on:
            raise RuntimeError(f"fake R2 failure for src_key={src_key}")
        new_key = f"cold/{src_key}"
        self.moves.append((src_key, new_key))
        return new_key
