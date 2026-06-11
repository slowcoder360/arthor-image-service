"""Load approved desktop hero assets as OpenAI edit references for mobile reframing."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from app.storage.uploader import browser_url_for

logger = logging.getLogger(__name__)

DESKTOP_SEED_EDIT_MODIFIER = (
    "Reframe this approved desktop hero for portrait mobile: preserve the same people, "
    "setting, and scene identity; adjust composition for stacked headline copy in the "
    "upper quiet zone."
)

_DESKTOP_SEED_POLL_INTERVAL_S = 5.0
_DESKTOP_SEED_WAIT_S = 600.0


async def _fetch_bytes_for_asset(services: Any, *, r2_key: str | None, r2_url: str | None) -> bytes:
    if r2_key and getattr(services, "r2", None) is not None:
        r2 = services.r2
        client = getattr(r2, "client", None)
        bucket = getattr(r2, "bucket", None)
        if client is not None and bucket:
            resp = await client.get_object(Bucket=bucket, Key=r2_key)
            body = resp["Body"]
            data = await body.read()
            return bytes(data)

    url = browser_url_for(
        services.settings,
        r2_key=r2_key,
        stored_url=r2_url,
    )
    fetcher = getattr(services, "reference_url_fetcher", None)
    if fetcher is not None:
        return await fetcher(url)

    import httpx

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def load_hero_asset_bytes(
    pool: Any,
    services: Any,
    asset_id: uuid.UUID,
) -> bytes:
    """Fetch uploaded hero asset bytes by id (regenerate mobile_from_desktop path)."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT status, r2_key, r2_url, metadata
            FROM external_media_assets
            WHERE id = $1
            """,
            asset_id,
        )
    if row is None or str(row["status"]) != "uploaded":
        raise ValueError("desktop_seed_asset_not_uploaded")
    md = row["metadata"]
    if isinstance(md, str):
        md = json.loads(md)
    if not isinstance(md, dict) or not md.get("hero_candidate"):
        raise ValueError("desktop_seed_asset_not_hero_candidate")
    return await _fetch_bytes_for_asset(
        services,
        r2_key=str(row["r2_key"]) if row.get("r2_key") else None,
        r2_url=str(row["r2_url"]) if row.get("r2_url") else None,
    )


async def _query_desktop_seed_rows(pool: Any, desktop_run_id: uuid.UUID) -> list[Any]:
    async with pool.acquire() as conn:
        run_row = await conn.fetchrow(
            """
            SELECT metadata FROM agent_runs
            WHERE id = $1 AND run_type = 'hero_candidates_generation'
            """,
            desktop_run_id,
        )
        if run_row is None:
            raise ValueError("desktop_seed_run_not_found")
        md = run_row["metadata"]
        if isinstance(md, str):
            md = json.loads(md)
        if not isinstance(md, dict) or md.get("hero_viewport", "desktop") != "desktop":
            raise ValueError("desktop_seed_run_not_desktop")

        return await conn.fetch(
            """
            SELECT r2_key, r2_url, status, metadata
            FROM external_media_assets
            WHERE agent_run_id = $1
              AND status = 'uploaded'
              AND metadata->>'hero_candidate' = 'true'
              AND metadata->>'variant_index' IS NOT NULL
            ORDER BY (metadata->>'variant_index')::int ASC
            """,
            desktop_run_id,
        )


async def load_desktop_seed_map(
    pool: Any,
    services: Any,
    desktop_run_id: uuid.UUID,
    *,
    wait: bool = True,
) -> dict[int, bytes]:
    """Map variant_index → desktop PNG bytes; optional poll until triad is uploaded."""
    deadline = time.monotonic() + (_DESKTOP_SEED_WAIT_S if wait else 0.0)

    while True:
        rows = await _query_desktop_seed_rows(pool, desktop_run_id)
        out: dict[int, bytes] = {}
        for row in rows:
            md = row["metadata"]
            if isinstance(md, str):
                md = json.loads(md)
            if not isinstance(md, dict):
                continue
            idx = md.get("variant_index")
            if idx is None:
                continue
            idx_int = int(idx)
            if idx_int in out:
                continue
            out[idx_int] = await _fetch_bytes_for_asset(
                services,
                r2_key=str(row["r2_key"]) if row.get("r2_key") else None,
                r2_url=str(row["r2_url"]) if row.get("r2_url") else None,
            )

        if len(out) >= 3:
            return out

        if not wait or time.monotonic() >= deadline:
            raise ValueError("desktop_seed_not_ready")
        await asyncio.sleep(_DESKTOP_SEED_POLL_INTERVAL_S)
