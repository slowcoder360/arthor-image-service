"""s10 AC-4: valid request → 202 + agent_runs row + image_request_payloads row."""

from __future__ import annotations

import json
import os

import pytest

from _helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_endpoint_accepts_valid_payload_returns_202_and_persists_rows(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])

    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: app/auth + asyncpg must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    payload = build_payload()
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/asset-pack/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )

    assert resp.status_code == 202, (
        f"AC-4: valid first-time POST must 202; got {resp.status_code} {resp.text!r}"
    )
    body = resp.json()
    assert "agent_run_id" in body, "AC-4: 202 body must include 'agent_run_id'"
    assert body.get("status") == "accepted", (
        f"AC-4: 202 body status must be 'accepted'; got {body.get('status')!r}"
    )

    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            run_row = await conn.fetchrow(
                "SELECT id FROM agent_runs WHERE id = $1", body["agent_run_id"]
            )
            irp_row = await conn.fetchrow(
                "SELECT id FROM image_request_payloads WHERE idempotency_key = $1",
                payload["idempotency_key"],
            )
        assert run_row is not None, (
            "AC-4: agent_runs row must be persisted before 202 is returned"
        )
        assert irp_row is not None, (
            "AC-4: image_request_payloads row must be persisted before 202 is returned"
        )
    finally:
        await pool.close()
