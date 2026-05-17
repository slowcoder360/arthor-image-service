"""s04 AC-6: insert_payload_record persists row, payload_hash matches canonical-JSON sha256."""

from __future__ import annotations

import hashlib
import json
import os
import uuid

import pytest

from _payload_fixtures import mvp_payload


def _canonical_hash(payload_dict: dict) -> str:
    canonical = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_insert_payload_record_persists_and_hashes():
    try:
        import asyncpg
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.payload.repository import insert_payload_record  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: dependencies must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        run_id = uuid.uuid4()
        idem_key = f"insert-{uuid.uuid4()}"
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')", run_id
            )

        raw = mvp_payload()
        raw["idempotency_key"] = idem_key
        payload = PayloadV1.model_validate(raw)
        row_id = await insert_payload_record(
            pool,
            agent_run_id=run_id,
            payload=payload,
            payload_version="1.0",
            idempotency_key=idem_key,
        )
        assert isinstance(row_id, uuid.UUID), (
            "AC-6: insert_payload_record must return a UUID row id"
        )

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT payload_hash, idempotency_key FROM image_request_payloads WHERE id = $1",
                row_id,
            )
        assert row is not None, "AC-6: row must be persisted"
        expected_hash = _canonical_hash(payload.model_dump(mode="json"))
        assert row["payload_hash"] == expected_hash, (
            "AC-6: payload_hash must match sha256 of canonical-JSON-encoded payload"
        )

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_duplicate_idempotency_key_raises_idempotency_conflict():
    try:
        import asyncpg
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.payload.repository import (  # type: ignore[import-not-found]
            IdempotencyConflict,
            insert_payload_record,
        )
    except ImportError as exc:
        pytest.fail(f"AC-6: dependencies must be importable ({exc})")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        run_id = uuid.uuid4()
        idem_key = f"dup-{uuid.uuid4()}"
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')", run_id
            )

        raw = mvp_payload()
        raw["idempotency_key"] = idem_key
        payload = PayloadV1.model_validate(raw)
        await insert_payload_record(
            pool,
            agent_run_id=run_id,
            payload=payload,
            payload_version="1.0",
            idempotency_key=idem_key,
        )
        with pytest.raises(IdempotencyConflict):
            await insert_payload_record(
                pool,
                agent_run_id=run_id,
                payload=payload,
                payload_version="1.0",
                idempotency_key=idem_key,
            )

        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
    finally:
        await pool.close()
