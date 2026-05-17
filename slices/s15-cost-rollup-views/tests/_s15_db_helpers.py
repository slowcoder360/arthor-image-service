"""Shared DB helpers for s15 cost-rollup tests."""

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


async def seed_run_with_cost(
    conn,
    *,
    cost_cents: int,
    site_id: uuid.UUID | None = None,
    run_type: str = "image_pack_generation",
    provider: str = "openai_image",
    slot_id: str = "s-0",
    slot_kind: str = "hero",
    started_at: datetime | None = None,
) -> uuid.UUID:
    """Insert one agent_run + tool_call + external_media_asset + payload row.

    Returns run_id. The tool_call has the requested cost_cents/provider and the
    asset metadata has the requested slot_id; the payload includes a `slots`
    array containing slot_kind for the rollup-by-slot-type query.
    """
    run_id = uuid.uuid4()
    site_id = site_id or uuid.uuid4()
    started = started_at or datetime.now(timezone.utc)
    await conn.execute(
        """
        INSERT INTO agent_runs
          (id, run_type, status, site_id, metadata, cost_cents, started_at, finished_at)
        VALUES ($1, $2, 'complete', $3, $4::jsonb, $5, $6, $6)
        """,
        run_id,
        run_type,
        site_id,
        json.dumps({"site_id": str(site_id)}),
        cost_cents,
        started,
    )
    payload_dict = {
        "payload_version": "1.0",
        "slots": [{"slot_id": slot_id, "slot_kind": slot_kind}],
    }
    await conn.execute(
        """
        INSERT INTO image_request_payloads (agent_run_id, idempotency_key, payload)
        VALUES ($1, $2, $3::jsonb)
        """,
        run_id,
        f"s15-{run_id}",
        json.dumps(payload_dict),
    )
    asset_id = uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO external_media_assets
          (id, provider, status, agent_run_id, site_id, metadata, r2_url)
        VALUES ($1, $2, 'uploaded', $3, $4, $5::jsonb, $6)
        """,
        asset_id,
        provider,
        run_id,
        site_id,
        json.dumps({"slot_id": slot_id}),
        f"https://r2.example.com/{asset_id}.png",
    )
    await conn.execute(
        """
        INSERT INTO tool_calls
          (id, run_id, provider, model_version, status, cost_cents, latency_ms)
        VALUES ($1, $2, $3, 'm', 'ok', $4, 100)
        """,
        uuid.uuid4(),
        run_id,
        provider,
        cost_cents,
    )
    return run_id


async def cleanup_run(conn, run_id: uuid.UUID) -> None:
    await conn.execute(
        "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
    )
    await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
    await conn.execute(
        "DELETE FROM image_request_payloads WHERE agent_run_id = $1", run_id
    )
    await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
