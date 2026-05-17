"""s10 AC-1: POST without X-Arthor-Signature returns 401."""

from __future__ import annotations

import json

import pytest

from _helpers import build_payload


@pytest.mark.asyncio
async def test_endpoint_rejects_unsigned_request(monkeypatch, tmp_path):
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/asset-pack/generate",
            content=json.dumps(build_payload()).encode(),
        )
    assert resp.status_code == 401, (
        f"AC-1: unsigned POST must 401; got {resp.status_code} {resp.text!r}"
    )
