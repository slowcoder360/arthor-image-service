"""s11 AC-3: unknown asset_id → 404."""

from __future__ import annotations

import json
import os
import uuid

import pytest


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_regenerate_unknown_asset_id_returns_404(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app + sign_body must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    body = {"asset_id": str(uuid.uuid4()), "new_seed": 7}
    raw = json.dumps(body).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/regenerate-slot",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
    assert resp.status_code == 404, (
        f"AC-3: unknown asset_id must 404; got {resp.status_code} {resp.text!r}"
    )
