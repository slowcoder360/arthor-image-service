"""Daily cold-storage rotation: superseded R2 assets older than 30 days → cold/ prefix."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.runtime import RuntimeServices
from app.storage import move_to_cold_storage as storage_move_to_cold

logger = logging.getLogger(__name__)

_ELIGIBILITY_SQL = """
SELECT id, r2_key FROM external_media_assets
WHERE status = 'superseded'
  AND updated_at < (now() - interval '30 days')
  AND r2_key IS NOT NULL
  AND r2_key NOT LIKE 'cold/%'
ORDER BY id
"""

_UPDATE_SQL = """
UPDATE external_media_assets
SET r2_key = $1,
    r2_url = NULL,
    updated_at = now(),
    metadata = metadata || jsonb_build_object('cold_storage_moved_at', to_jsonb(now()::timestamptz))
WHERE id = $2
"""


async def _move_to_cold_storage(r2: Any, *, src_key: str) -> str:
    """Resolve move: storage helper, or ``r2.move_to_cold_storage`` for doubles."""
    mover = getattr(r2, "move_to_cold_storage", None)
    if callable(mover):
        return await mover(src_key=src_key)
    return await storage_move_to_cold(r2, src_key=src_key)


async def sweep_once(pool: Any, r2: Any) -> int:
    """Run one eligibility sweep; return count of rows successfully rotated."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(_ELIGIBILITY_SQL)
    moved = 0
    for row in rows:
        asset_id = row["id"]
        src_key = row["r2_key"]
        try:
            new_key = await _move_to_cold_storage(r2, src_key=src_key)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "cold_storage sweep: move failed asset_id=%s src_key=%s",
                asset_id,
                src_key,
            )
            continue
        try:
            async with pool.acquire() as conn:
                await conn.execute(_UPDATE_SQL, new_key, asset_id)
            moved += 1
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "cold_storage sweep: DB update failed after R2 move asset_id=%s",
                asset_id,
            )
    return moved


async def cold_storage_worker(services: RuntimeServices) -> None:
    interval = services.settings.cold_storage_interval_seconds
    if interval == 0:
        return
    while True:
        try:
            pool, r2 = services.pool, services.r2
            if pool is not None and r2 is not None:
                await sweep_once(pool, r2)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("cold_storage_worker iteration failed")
        await asyncio.sleep(interval)
