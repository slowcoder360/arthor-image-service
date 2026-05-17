"""s11 AC-6: new agent_runs row has run_type='image_slot_regenerate',
parent_run_id=<original_run_id>, metadata.original_asset_id=<old_asset_id>.

Exercises the route via HTTP so the row is created the way the route inserts it.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest

from _s11_helpers import build_payload, cleanup_run, seed_prior_pack_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_regenerate_new_run_lineage(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: app + sign_body + asyncpg must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    payload = build_payload()
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    new_run_id = None
    old_run_id = None
    try:
        async with pool.acquire() as conn:
            old_run_id, old_asset_id = await seed_prior_pack_run(conn, payload)

        body = {"asset_id": str(old_asset_id), "new_seed": 7}
        raw = json.dumps(body).encode()
        sig = sign_body("k", raw)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/images/regenerate-slot",
                content=raw,
                headers={"X-Arthor-Signature": sig},
            )
        assert resp.status_code == 202, (
            f"AC-6: regenerate must 202 + return new run/asset ids; got "
            f"{resp.status_code} {resp.text!r}"
        )
        rbody = resp.json()
        assert "agent_run_id" in rbody, "AC-6: 202 body must contain agent_run_id"
        assert "new_asset_id" in rbody, "AC-6: 202 body must contain new_asset_id"
        new_run_id = uuid.UUID(rbody["agent_run_id"])

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT run_type, parent_run_id, metadata
                FROM agent_runs WHERE id = $1
                """,
                new_run_id,
            )
        assert row is not None, "AC-6: new agent_runs row must exist after 202"
        assert row["run_type"] == "image_slot_regenerate", (
            f"AC-6: new run_type must be 'image_slot_regenerate'; got {row['run_type']!r}"
        )
        assert row["parent_run_id"] == old_run_id, (
            f"AC-6: parent_run_id must equal the original run_id; "
            f"got {row['parent_run_id']!r} vs {old_run_id!r}"
        )
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        assert str(meta.get("original_asset_id")) == str(old_asset_id), (
            f"AC-6: metadata.original_asset_id must equal old asset id; "
            f"got {meta.get('original_asset_id')!r} vs {old_asset_id!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if new_run_id is not None:
                await cleanup_run(conn, new_run_id)
            if old_run_id is not None:
                await cleanup_run(conn, old_run_id)
        await pool.close()
