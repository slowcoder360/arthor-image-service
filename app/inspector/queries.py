"""Read-only asyncpg queries for inspector list and detail views."""

from __future__ import annotations

import json
import math
import uuid
from typing import Any

import asyncpg

_IMAGE_RUN_TYPES = (
    "image_pack_generation",
    "image_slot_regenerate",
    "image_style_preview",
)

_PAGE_SIZE = 25


def normalize_run_type_filter(raw: str | None) -> str | None:
    if raw is None or raw == "":
        return None
    if raw not in _IMAGE_RUN_TYPES:
        raise ValueError("invalid run_type")
    return raw


async def count_runs(conn: asyncpg.Connection, run_type: str | None) -> int:
    if run_type:
        return int(
            await conn.fetchval(
                """
                SELECT COUNT(*) FROM agent_runs
                WHERE run_type IN (
                    'image_pack_generation',
                    'image_slot_regenerate',
                    'image_style_preview'
                )
                  AND run_type = $1
                """,
                run_type,
            )
            or 0
        )
    return int(
        await conn.fetchval(
            """
            SELECT COUNT(*) FROM agent_runs
            WHERE run_type IN (
                'image_pack_generation',
                'image_slot_regenerate',
                'image_style_preview'
            )
            """
        )
        or 0
    )


async def fetch_runs_page(
    conn: asyncpg.Connection,
    *,
    run_type: str | None,
    page: int,
) -> list[asyncpg.Record]:
    offset = max(page - 1, 0) * _PAGE_SIZE
    if run_type:
        return await conn.fetch(
            """
            SELECT id, run_type, status, started_at, finished_at, cost_cents
            FROM agent_runs
            WHERE run_type IN (
                'image_pack_generation',
                'image_slot_regenerate',
                'image_style_preview'
            )
              AND run_type = $1
            ORDER BY started_at DESC NULLS LAST
            LIMIT $2 OFFSET $3
            """,
            run_type,
            _PAGE_SIZE,
            offset,
        )
    return await conn.fetch(
        """
        SELECT id, run_type, status, started_at, finished_at, cost_cents
        FROM agent_runs
        WHERE run_type IN (
            'image_pack_generation',
            'image_slot_regenerate',
            'image_style_preview'
        )
        ORDER BY started_at DESC NULLS LAST
        LIMIT $1 OFFSET $2
        """,
        _PAGE_SIZE,
        offset,
    )


async def fetch_run_row(
    conn: asyncpg.Connection, run_id: uuid.UUID
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT id, run_type, status, started_at, finished_at, cost_cents, metadata
        FROM agent_runs
        WHERE id = $1
        """,
        run_id,
    )


async def fetch_payload(
    conn: asyncpg.Connection, run_id: uuid.UUID
) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT payload, payload_version, idempotency_key, created_at
        FROM image_request_payloads
        WHERE agent_run_id = $1
        ORDER BY created_at ASC
        LIMIT 1
        """,
        run_id,
    )


async def fetch_assets(
    conn: asyncpg.Connection, run_id: uuid.UUID
) -> list[asyncpg.Record]:
    rows = await conn.fetch(
        """
        SELECT id, provider, status, model_version, r2_url, metadata, created_at
        FROM external_media_assets
        WHERE agent_run_id = $1
        ORDER BY COALESCE(metadata->>'slot_id', ''), created_at ASC
        """,
        run_id,
    )
    return list(rows)


async def fetch_tool_calls(
    conn: asyncpg.Connection, run_id: uuid.UUID
) -> list[asyncpg.Record]:
    rows = await conn.fetch(
        """
        SELECT id, provider, model_version, status, cost_cents, latency_ms,
               args, result, created_at
        FROM tool_calls
        WHERE run_id = $1
        ORDER BY created_at ASC
        """,
        run_id,
    )
    return list(rows)


def page_count(total: int) -> int:
    if total <= 0:
        return 1
    return max(1, math.ceil(total / _PAGE_SIZE))


def style_profile_from_run_metadata(metadata: Any) -> Any:
    if metadata is None:
        return None
    if isinstance(metadata, dict):
        return metadata.get("style_profile")
    try:
        data = json.loads(metadata)
    except (TypeError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        return data.get("style_profile")
    return None


async def load_run_detail(
    pool: asyncpg.pool.Pool,
    run_id: uuid.UUID,
) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        run = await fetch_run_row(conn, run_id)
        if run is None:
            return None
        payload_row = await fetch_payload(conn, run_id)
        assets = await fetch_assets(conn, run_id)
        tool_calls = await fetch_tool_calls(conn, run_id)
    meta = run["metadata"]
    style_profile = style_profile_from_run_metadata(meta)
    return {
        "run": run,
        "payload_row": payload_row,
        "style_profile": style_profile,
        "assets": assets,
        "tool_calls": tool_calls,
    }


async def load_runs_list(
    pool: asyncpg.pool.Pool,
    *,
    page: int,
    run_type: str | None,
) -> tuple[list[asyncpg.Record], int, int]:
    page = max(page, 1)
    async with pool.acquire() as conn:
        total = await count_runs(conn, run_type)
        rows = await fetch_runs_page(conn, run_type=run_type, page=page)
    return rows, total, page_count(total)


async def fetch_slot_variants(
    pool: asyncpg.pool.Pool,
    *,
    slot_id: str,
    anchor_run_id: uuid.UUID,
) -> list[asyncpg.Record]:
    """Slot history: assets for ``slot_id`` on this run or its direct child runs."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ema.id, ema.provider, ema.status, ema.model_version, ema.r2_url,
                   ema.metadata, ema.created_at, ar.cost_cents
            FROM external_media_assets ema
            INNER JOIN agent_runs ar ON ar.id = ema.agent_run_id
            WHERE ema.metadata->>'slot_id' = $1
              AND ema.agent_run_id IN (
                  SELECT id FROM agent_runs
                  WHERE id = $2 OR parent_run_id = $2
              )
            ORDER BY ema.created_at ASC
            """,
            slot_id,
            anchor_run_id,
        )
    return list(rows)


async def fetch_pack_grid_assets(
    pool: asyncpg.pool.Pool,
    run_id: uuid.UUID,
) -> list[asyncpg.Record]:
    """All ``uploaded`` assets for a pack run (consistency grid)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, provider, status, model_version, r2_url, metadata, created_at
            FROM external_media_assets
            WHERE agent_run_id = $1 AND status = 'uploaded'
            ORDER BY metadata->>'slot_id'
            """,
            run_id,
        )
    return list(rows)
