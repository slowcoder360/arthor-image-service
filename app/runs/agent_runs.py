"""Writers for harness-flavored ``agent_runs`` rows (ADR-0004)."""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg

_ALLOWED_RUN_TYPES = frozenset(
    {
        "image_pack_generation",
        "image_slot_regenerate",
        "image_style_preview",
    }
)
_ALLOWED_STATUS = frozenset({"running", "ok", "failed"})


def _validate_run_type(run_type: str) -> None:
    if run_type not in _ALLOWED_RUN_TYPES:
        raise ValueError(f"unsupported run_type: {run_type!r}")


def _validate_status(status: str) -> None:
    if status not in _ALLOWED_STATUS:
        raise ValueError(f"unsupported status: {status!r}")


def _build_insert_metadata(
    *,
    site_id: uuid.UUID | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(metadata or {})
    if site_id is not None:
        merged["site_id"] = str(site_id)
    return merged


async def insert_pending_run(
    pool: asyncpg.pool.Pool,
    *,
    run_type: str,
    site_id: uuid.UUID | None,
    parent_run_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> uuid.UUID:
    """Insert a ``running`` run with counters zeroed; returns ``agent_runs.id``."""
    _validate_run_type(run_type)
    meta = _build_insert_metadata(site_id=site_id, metadata=metadata)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO agent_runs (
              run_type, status, started_at, finished_at,
              cost_cents, prompt_tokens, completion_tokens,
              metadata, parent_run_id
            )
            VALUES (
              $1, 'running', now(), NULL,
              0, 0, 0,
              $2::jsonb, $3
            )
            RETURNING id
            """,
            run_type,
            meta,
            parent_run_id,
        )
    assert row is not None
    return row["id"]


async def update_run_status(
    pool: asyncpg.pool.Pool,
    run_id: uuid.UUID,
    *,
    status: str,
    error: str | None = None,
    finished: bool = False,
    metadata_patch: dict[str, Any] | None = None,
) -> None:
    """Update ``status``; optionally finish the run and shallow-merge ``metadata``."""
    _validate_status(status)

    meta_patch: dict[str, Any] = {}
    if metadata_patch:
        meta_patch.update(metadata_patch)
    if error is not None:
        meta_patch["error"] = error

    async with pool.acquire() as conn:
        if finished:
            if meta_patch:
                await conn.execute(
                    """
                    UPDATE agent_runs
                    SET status = $2,
                        finished_at = now(),
                        metadata = COALESCE(metadata, '{}'::jsonb) || $3::jsonb
                    WHERE id = $1
                    """,
                    run_id,
                    status,
                    meta_patch,
                )
            else:
                await conn.execute(
                    """
                    UPDATE agent_runs
                    SET status = $2,
                        finished_at = now()
                    WHERE id = $1
                    """,
                    run_id,
                    status,
                )
        elif meta_patch:
            await conn.execute(
                """
                UPDATE agent_runs
                SET status = $2,
                    metadata = COALESCE(metadata, '{}'::jsonb) || $3::jsonb
                WHERE id = $1
                """,
                run_id,
                status,
                meta_patch,
            )
        else:
            await conn.execute(
                """
                UPDATE agent_runs
                SET status = $2
                WHERE id = $1
                """,
                run_id,
                status,
            )
