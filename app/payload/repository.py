"""Persistence helpers for validated payloads."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

import asyncpg

from app.payload.models import PayloadV1


class IdempotencyConflict(Exception):
    """Raised when reusing ``idempotency_key`` violates the UNIQUE index."""

    pass


async def insert_payload_record(
    pool: asyncpg.pool.Pool,
    *,
    agent_run_id: uuid.UUID,
    payload: PayloadV1,
    payload_version: str,
    idempotency_key: str,
    source: str = "arthor-ai",
) -> uuid.UUID:
    """Persist a payload row returning ``image_request_payloads.id``."""
    blob = payload.model_dump(mode="json")
    canonical = json.dumps(blob, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO image_request_payloads
                  (agent_run_id, payload_version, payload, payload_hash, idempotency_key, source)
                VALUES ($1, $2, $3::jsonb, $4, $5, $6)
                RETURNING id
                """,
                agent_run_id,
                payload_version,
                canonical,
                digest,
                idempotency_key,
                source,
            )
    except asyncpg.UniqueViolationError as exc:
        raise IdempotencyConflict(str(exc)) from exc

    assert row is not None
    return row["id"]


async def insert_raw_payload_record(
    pool: asyncpg.pool.Pool,
    *,
    agent_run_id: uuid.UUID,
    payload: dict[str, Any],
    payload_version: str,
    idempotency_key: str,
    source: str = "arthor-ai",
) -> uuid.UUID:
    """Persist an arbitrary JSON payload (hero-candidates narrow contract)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO image_request_payloads
                  (agent_run_id, payload_version, payload, payload_hash, idempotency_key, source)
                VALUES ($1, $2, $3::jsonb, $4, $5, $6)
                RETURNING id
                """,
                agent_run_id,
                payload_version,
                canonical,
                digest,
                idempotency_key,
                source,
            )
    except asyncpg.UniqueViolationError as exc:
        raise IdempotencyConflict(str(exc)) from exc

    assert row is not None
    return row["id"]
