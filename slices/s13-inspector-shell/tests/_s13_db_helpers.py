"""Shared DB helpers for s13 inspector tests."""

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


async def seed_run(
    conn,
    *,
    run_id: uuid.UUID | None = None,
    run_type: str = "image_pack_generation",
    status: str = "complete",
    site_id: uuid.UUID | None = None,
    payload: dict | None = None,
    style_profile: dict | None = None,
    asset_count: int = 1,
    palette_drift: bool = False,
) -> tuple[uuid.UUID, list[uuid.UUID]]:
    """Insert a run + payload + N asset rows + one tool_calls row.

    Returns (run_id, [asset_ids]).
    """
    run_id = run_id or uuid.uuid4()
    site_id = site_id or uuid.uuid4()
    payload = payload or {"payload_version": "1.0", "site_id": str(site_id)}
    metadata = {"site_id": str(site_id), "style_profile": style_profile or {}}

    await conn.execute(
        """
        INSERT INTO agent_runs (id, run_type, status, site_id, metadata, cost_cents)
        VALUES ($1, $2, $3, $4, $5::jsonb, 12)
        """,
        run_id,
        run_type,
        status,
        site_id,
        json.dumps(metadata),
    )
    await conn.execute(
        """
        INSERT INTO image_request_payloads (agent_run_id, idempotency_key, payload)
        VALUES ($1, $2, $3::jsonb)
        """,
        run_id,
        f"s13-{run_id}",
        json.dumps(payload),
    )
    asset_ids: list[uuid.UUID] = []
    for i in range(asset_count):
        aid = uuid.uuid4()
        asset_ids.append(aid)
        meta = {"slot_id": f"s-{i}", "seed": 100 + i, "prompt_hash": f"hash{i:02d}"}
        if palette_drift:
            meta["palette_drift"] = True
        await conn.execute(
            """
            INSERT INTO external_media_assets
              (id, provider, status, agent_run_id, site_id, metadata, r2_url)
            VALUES ($1, 'openai_image', 'uploaded', $2, $3, $4::jsonb, $5)
            """,
            aid,
            run_id,
            site_id,
            json.dumps(meta),
            f"https://r2.example.com/{aid}.png",
        )
    await conn.execute(
        """
        INSERT INTO tool_calls
          (id, run_id, provider, model_version, status, cost_cents, latency_ms)
        VALUES ($1, $2, 'openai_image', 'gpt-image-1', 'ok', 12, 1000)
        """,
        uuid.uuid4(),
        run_id,
    )
    return run_id, asset_ids


async def cleanup_run(conn, run_id: uuid.UUID) -> None:
    await conn.execute(
        "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
    )
    await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
    await conn.execute(
        "DELETE FROM image_request_payloads WHERE agent_run_id = $1", run_id
    )
    await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
