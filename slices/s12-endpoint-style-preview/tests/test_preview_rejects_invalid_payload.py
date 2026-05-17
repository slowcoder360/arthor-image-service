"""s12 AC-2 + AC-8: invalid payload (missing required fields) → 400."""

from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_preview_rejects_invalid_payload(monkeypatch, tmp_path):
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

    invalid_body = {"payload_version": "1.0", "idempotency_key": "k"}
    raw = json.dumps(invalid_body).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/style-profile/preview",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
    assert resp.status_code == 400, (
        f"AC-2/AC-8: invalid payload must 400; got {resp.status_code} {resp.text!r}"
    )
