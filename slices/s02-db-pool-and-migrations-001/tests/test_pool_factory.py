"""s02 AC-1: db/pool.py exposes init_pool / close_pool around an asyncpg.Pool."""

from __future__ import annotations

import os

import pytest


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_init_pool_returns_asyncpg_pool_and_close_pool_cleans_up():
    try:
        import asyncpg
    except ImportError as exc:
        pytest.fail(f"asyncpg is not installed in the test environment: {exc}")

    try:
        from db.pool import close_pool, init_pool  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-1: `db.pool.init_pool`/`close_pool` must be importable; not yet implemented ({exc})"
        )

    database_url = os.environ["DATABASE_URL"]
    pool = await init_pool(database_url)
    assert isinstance(pool, asyncpg.Pool), (
        "AC-1: init_pool must return an asyncpg.Pool instance"
    )
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1, "AC-1: pool must be usable after init_pool returns"
    await close_pool(pool)


def test_init_pool_signature_matches_adr_0002(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    try:
        from db.pool import init_pool  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-1: `db.pool.init_pool` must be importable; not yet implemented ({exc})"
        )
    import inspect

    sig = inspect.signature(init_pool)
    params = list(sig.parameters)
    assert params == ["database_url"], (
        "AC-1: init_pool(database_url: str) — signature must take exactly one positional 'database_url' arg "
        f"(per ADR-0002 / arthor-agent mirror); got {params}"
    )
