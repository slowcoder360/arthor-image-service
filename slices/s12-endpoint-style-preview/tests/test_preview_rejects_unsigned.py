"""s12 AC-1: POST /images/style-profile/preview without HMAC → 401."""

from __future__ import annotations

import json

import pytest

from _s12_helpers import build_payload


@pytest.mark.asyncio
async def test_preview_rejects_unsigned(monkeypatch, tmp_path):
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

    raw = json.dumps(build_payload()).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/style-profile/preview", content=raw
        )
    assert resp.status_code == 401, (
        f"AC-1: unsigned POST must 401; got {resp.status_code} {resp.text!r}"
    )
