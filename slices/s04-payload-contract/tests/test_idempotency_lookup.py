"""s04 AC-5: lookup_idempotency_key returns agent_run_id or None against the DB."""

from __future__ import annotations

import os
import uuid

import pytest


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_idempotency_lookup_unknown_returns_none():
    try:
        import asyncpg
        from app.payload.idempotency import (  # type: ignore[import-not-found]
            lookup_idempotency_key,
        )
    except ImportError as exc:
        pytest.fail(
            f"AC-5: `app.payload.idempotency.lookup_idempotency_key` and asyncpg must be importable ({exc})"
        )

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        result = await lookup_idempotency_key(pool, "this-key-does-not-exist-xyz123")
        assert result is None, (
            "AC-5: unknown idempotency_key must return None"
        )
    finally:
        await pool.close()


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_idempotency_lookup_known_returns_agent_run_id():
    try:
        import asyncpg
        from app.payload.idempotency import (  # type: ignore[import-not-found]
            lookup_idempotency_key,
        )
    except ImportError as exc:
        pytest.fail(f"AC-5: dependencies must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        run_id = uuid.uuid4()
        idem_key = f"test-{uuid.uuid4()}"

        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')",
                run_id,
            )
            await conn.execute(
                "INSERT INTO image_request_payloads "
                "(agent_run_id, payload_version, payload, payload_hash, idempotency_key) "
                "VALUES ($1, '1.0', '{}'::jsonb, 'hash_zero', $2)",
                run_id,
                idem_key,
            )

        result = await lookup_idempotency_key(pool, idem_key)
        assert result == run_id, (
            f"AC-5: known idempotency_key must return associated agent_run_id; got {result}"
        )

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()
