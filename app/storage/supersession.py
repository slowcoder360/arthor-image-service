"""Uploaded asset supersession helpers."""

from __future__ import annotations

import uuid

import asyncpg

from app.storage.asset_writer import InvalidStateTransition


class UnsupersedeUnavailable(RuntimeError):
    """Raised when ``unsupersede_asset`` preconditions are not met."""


async def supersede_asset(
    pool: asyncpg.pool.Pool,
    *,
    old_asset_id: uuid.UUID,
    new_asset_id: uuid.UUID,
) -> None:
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE external_media_assets
            SET status = 'superseded',
                metadata = metadata || jsonb_build_object(
                    'replaced_by', $2::text
                ),
                updated_at = now()
            WHERE id = $1 AND status = 'uploaded'
            """,
            old_asset_id,
            str(new_asset_id),
        )
    if not str(result).startswith("UPDATE 1"):
        raise InvalidStateTransition(
            f"supersede_asset requires status 'uploaded' for old_asset_id={old_asset_id}"
        )


async def unsupersede_asset(pool: asyncpg.pool.Pool, *, asset_id: uuid.UUID) -> None:
    """Restore ``superseded → uploaded`` if the replacing row still exists."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE external_media_assets AS ema
            SET status = 'uploaded',
                metadata = ema.metadata - 'replaced_by',
                updated_at = now()
            WHERE ema.id = $1
              AND ema.status = 'superseded'
              AND ema.metadata ? 'replaced_by'
              AND EXISTS (
                  SELECT 1
                  FROM external_media_assets AS repl
                  WHERE repl.id = (ema.metadata->>'replaced_by')::uuid
              )
            RETURNING ema.id
            """,
            asset_id,
        )
    if row is None:
        raise UnsupersedeUnavailable(
            f"unsupersede_asset unavailable for asset_id={asset_id}"
        )
