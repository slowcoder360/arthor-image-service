"""``external_media_assets`` state-machine writers."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from typing import Any

import asyncpg

_REQUIRED_PENDING_METADATA_KEYS = frozenset(
    {
        "slot_id",
        "slot_intent",
        "style_profile_id",
        "prompt_hash",
        "seed",
        "determinism_level",
        "run_id",
    }
)


class InvalidStateTransition(RuntimeError):
    """Raised when a status transition is not allowed for the current row."""


def _validate_pending_metadata(metadata: Mapping[str, Any]) -> None:
    missing = sorted(_REQUIRED_PENDING_METADATA_KEYS - set(metadata.keys()))
    if missing:
        raise ValueError(f"metadata missing required keys: {', '.join(missing)}")


async def insert_pending_asset(
    pool: asyncpg.pool.Pool,
    *,
    agent_run_id: uuid.UUID,
    site_id: uuid.UUID,
    provider: str,
    model_version: str,
    metadata: dict[str, Any],
) -> uuid.UUID:
    _validate_pending_metadata(metadata)
    blob = json.dumps(metadata)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO external_media_assets
              (agent_run_id, site_id, provider, model_version, status, metadata)
            VALUES ($1, $2, $3, $4, 'pending', $5::jsonb)
            RETURNING id
            """,
            agent_run_id,
            site_id,
            provider,
            model_version,
            blob,
        )
    assert row is not None
    return row["id"]


async def mark_asset_generated(
    pool: asyncpg.pool.Pool,
    asset_id: uuid.UUID,
    *,
    width: int,
    height: int,
    bytes_len: int,
    external_id: str,
    metadata_patch: dict[str, Any] | None = None,
) -> None:
    async with pool.acquire() as conn:
        if metadata_patch:
            result = await conn.execute(
                """
                UPDATE external_media_assets
                SET status = 'generated',
                    width = $2,
                    height = $3,
                    bytes = $4,
                    external_id = $5,
                    metadata = metadata || $6::jsonb,
                    updated_at = now()
                WHERE id = $1 AND status = 'pending'
                """,
                asset_id,
                width,
                height,
                bytes_len,
                external_id,
                json.dumps(metadata_patch),
            )
        else:
            result = await conn.execute(
                """
                UPDATE external_media_assets
                SET status = 'generated',
                    width = $2,
                    height = $3,
                    bytes = $4,
                    external_id = $5,
                    updated_at = now()
                WHERE id = $1 AND status = 'pending'
                """,
                asset_id,
                width,
                height,
                bytes_len,
                external_id,
            )
    if not str(result).startswith("UPDATE 1"):
        raise InvalidStateTransition(
            f"mark_asset_generated expects status 'pending' for asset_id={asset_id}"
        )


async def mark_asset_uploaded(
    pool: asyncpg.pool.Pool,
    asset_id: uuid.UUID,
    *,
    r2_key: str,
    r2_url: str,
) -> None:
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE external_media_assets
            SET status = 'uploaded',
                r2_key = $2,
                r2_url = $3,
                updated_at = now()
            WHERE id = $1 AND status = ANY($4::text[])
            """,
            asset_id,
            r2_key,
            r2_url,
            ["pending", "generated"],
        )
    if not str(result).startswith("UPDATE 1"):
        raise InvalidStateTransition(
            f"mark_asset_uploaded expects status in ('pending','generated') for "
            f"asset_id={asset_id}"
        )


async def mark_asset_failed(
    pool: asyncpg.pool.Pool,
    asset_id: uuid.UUID,
    *,
    error: str,
) -> None:
    async with pool.acquire() as conn:
            error_blob = json.dumps({"error": error})
            result = await conn.execute(
                """
                UPDATE external_media_assets
                SET status = 'failed',
                    metadata = metadata || $2::jsonb,
                    updated_at = now()
                WHERE id = $1 AND status = ANY($3::text[])
                """,
                asset_id,
                error_blob,
                ["pending", "generated"],
            )
    if not str(result).startswith("UPDATE 1"):
        raise InvalidStateTransition(
            f"mark_asset_failed expects status in ('pending','generated') for asset_id={asset_id}"
        )
