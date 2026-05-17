"""s11 AC-1: POST /images/regenerate-slot without HMAC → 401."""

from __future__ import annotations

import json
import uuid

import pytest


@pytest.mark.asyncio
async def test_regenerate_rejects_unsigned(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    body = {"asset_id": str(uuid.uuid4()), "new_seed": 1}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/regenerate-slot", content=json.dumps(body).encode()
        )
    assert resp.status_code == 401, (
        f"AC-1: unsigned POST must 401; got {resp.status_code}"
    )
