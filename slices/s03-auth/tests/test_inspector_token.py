"""s03 AC-4: require_inspector_token — Bearer header / cookie / 503 / 401."""

from __future__ import annotations

import pytest


def _build_app(token: str | None):
    try:
        from fastapi import Depends, FastAPI
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"fastapi/httpx not installed: {exc}")
    try:
        from app.auth.inspector_token import require_inspector_token  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-4: `app.auth.inspector_token.require_inspector_token` must be importable ({exc})"
        )

    app = FastAPI()

    class _Settings:
        inspector_admin_token = token

    class _Services:
        settings = _Settings()

    app.state.services = _Services()

    @app.get("/admin")
    async def _admin(_: None = Depends(require_inspector_token)):
        return {"ok": True}

    return app, ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_require_inspector_token_503_when_unset():
    app, ASGITransport, AsyncClient = _build_app(token=None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/admin", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 503, (
        f"AC-4: must 503 when admin token unset, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_require_inspector_token_passes_with_bearer_header():
    app, ASGITransport, AsyncClient = _build_app(token="goodtoken")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/admin", headers={"Authorization": "Bearer goodtoken"})
    assert resp.status_code == 200, (
        f"AC-4: valid Bearer must pass, got {resp.status_code} {resp.text!r}"
    )


@pytest.mark.asyncio
async def test_require_inspector_token_passes_with_cookie():
    app, ASGITransport, AsyncClient = _build_app(token="goodtoken")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        client.cookies.set("arthor_inspector_token", "goodtoken")
        resp = await client.get("/admin")
    assert resp.status_code == 200, (
        f"AC-4: valid arthor_inspector_token cookie must pass, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_require_inspector_token_401_when_missing():
    app, ASGITransport, AsyncClient = _build_app(token="goodtoken")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/admin")
    assert resp.status_code == 401, (
        f"AC-4: missing both Bearer and cookie must 401, got {resp.status_code}"
    )


@pytest.mark.asyncio
async def test_require_inspector_token_401_on_mismatch():
    app, ASGITransport, AsyncClient = _build_app(token="goodtoken")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/admin", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401, (
        f"AC-4: Bearer mismatch must 401, got {resp.status_code}"
    )
