"""s11 AC-3: regenerating a non-uploaded asset → 400."""

from __future__ import annotations

import json
import os
import uuid

import pytest


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_regenerate_failed_asset_returns_400(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app + sign_body + asyncpg must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    run_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO agent_runs (id, status) VALUES ($1, 'pending')", run_id
            )
            await conn.execute(
                """
                INSERT INTO external_media_assets
                  (id, provider, status, agent_run_id, site_id, metadata)
                VALUES ($1, 'openai_image', 'failed', $2, $3, '{"slot_id":"s-0"}'::jsonb)
                """,
                asset_id,
                run_id,
                uuid.uuid4(),
            )

        body = {"asset_id": str(asset_id), "new_seed": 1}
        raw = json.dumps(body).encode()
        sig = sign_body("k", raw)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/images/regenerate-slot",
                content=raw,
                headers={"X-Arthor-Signature": sig},
            )
        assert resp.status_code == 400, (
            f"AC-3: regenerating a 'failed' asset must 400; got {resp.status_code} {resp.text!r}"
        )
    finally:
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM external_media_assets WHERE id = $1", asset_id
            )
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
        await pool.close()
