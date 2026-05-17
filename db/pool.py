"""asyncpg connection pool helpers (arthor-agent mirror)."""

from __future__ import annotations

import asyncpg


async def init_pool(database_url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(
        database_url,
        min_size=1,
        max_size=10,
    )


async def close_pool(pool: asyncpg.Pool | None) -> None:
    if pool is not None:
        await pool.close()
