"""Idempotency key lookup against persisted payloads."""

from __future__ import annotations

import uuid

import asyncpg


async def lookup_idempotency_key(
    pool: asyncpg.pool.Pool, key: str
) -> uuid.UUID | None:
    """Return ``agent_run_id`` linked to ``idempotency_key`` or ``None``."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT agent_run_id FROM image_request_payloads WHERE idempotency_key = $1",
            key,
        )
    if row is None:
        return None
    return row["agent_run_id"]
