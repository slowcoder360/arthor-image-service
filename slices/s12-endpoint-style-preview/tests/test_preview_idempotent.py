"""s12 AC-2: repeated previews with same `idempotency_key` return the prior asset_id."""

from __future__ import annotations

import json
import os
import uuid

import pytest

from _s12_helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_preview_idempotent_replay(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: app + sign_body + asyncpg must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    payload = build_payload(idem_key=f"s12-idem-{uuid.uuid4()}")
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    run_id = None
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", timeout=60.0
        ) as client:
            first = await client.post(
                "/images/style-profile/preview",
                content=raw,
                headers={"X-Arthor-Signature": sig},
            )
            assert first.status_code == 200, (
                f"AC-2: first preview must 200; got {first.status_code} {first.text!r}"
            )
            first_body = first.json()
            run_id = first_body["agent_run_id"]

            second = await client.post(
                "/images/style-profile/preview",
                content=raw,
                headers={"X-Arthor-Signature": sig},
            )
        assert second.status_code == 200, (
            f"AC-2: replay preview must 200; got {second.status_code} {second.text!r}"
        )
        second_body = second.json()
        assert second_body.get("asset_id") == first_body.get("asset_id"), (
            f"AC-2: replay must return the prior asset_id; "
            f"got first={first_body.get('asset_id')!r} second={second_body.get('asset_id')!r}"
        )
    finally:
        if run_id is not None:
            async with pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
                )
                await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
                await conn.execute(
                    "DELETE FROM image_request_payloads WHERE agent_run_id = $1", run_id
                )
                await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
        await pool.close()
