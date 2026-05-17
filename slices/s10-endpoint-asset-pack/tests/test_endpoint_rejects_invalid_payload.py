"""s10 AC-2: signed but invalid payload returns 400 with a structured ValidationReport."""

from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_endpoint_rejects_invalid_payload_with_400(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    try:
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: app + sign_body must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    incomplete = {"payload_version": "1.0", "idempotency_key": "abcdefgh"}
    raw = json.dumps(incomplete).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/asset-pack/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
    assert resp.status_code == 400, (
        f"AC-2: invalid payload must 400; got {resp.status_code} {resp.text!r}"
    )
    body = resp.json()
    assert "errors" in body or "detail" in body, (
        "AC-2: 400 body must include a structured ValidationReport with 'errors' (or 'detail' wrapping it)"
    )
