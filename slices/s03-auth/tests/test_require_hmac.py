"""s03 AC-3: require_hmac dependency 503/401/400/200 + caches raw_body on request.state."""

from __future__ import annotations

import pytest


def _build_app(secret: str | None):
    try:
        from fastapi import Depends, FastAPI, Request
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"fastapi/httpx not installed: {exc}")
    try:
        from app.auth.hmac import require_hmac  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-3: `app.auth.hmac.require_hmac` must be importable; not yet implemented ({exc})"
        )

    app = FastAPI()

    class _Settings:
        fastapi_arthor_shared_secret = secret

    class _Services:
        settings = _Settings()

    app.state.services = _Services()

    @app.post("/echo")
    async def _echo(request: Request, body: bytes = Depends(require_hmac)):
        return {
            "len": len(body),
            "raw_body_seen": getattr(request.state, "raw_body", None) == body,
        }

    return app, ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_require_hmac_503_when_secret_unset():
    app, ASGITransport, AsyncClient = _build_app(secret=None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/echo", content=b"hi")
    assert resp.status_code == 503, (
        f"AC-3: must 503 when secret unset, got {resp.status_code}"
    )
    assert resp.json().get("detail") == "hmac_secret_unset", (
        "AC-3: detail must be 'hmac_secret_unset' when secret is unset"
    )


@pytest.mark.asyncio
async def test_require_hmac_400_on_empty_body():
    app, ASGITransport, AsyncClient = _build_app(secret="k")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/echo", content=b"")
    assert resp.status_code == 400, (
        f"AC-3: must 400 on empty body, got {resp.status_code}"
    )
    assert resp.json().get("detail") == "empty_body", (
        "AC-3: detail must be 'empty_body' on empty body"
    )


@pytest.mark.asyncio
async def test_require_hmac_401_on_bad_sig():
    app, ASGITransport, AsyncClient = _build_app(secret="k")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/echo",
            content=b"hi",
            headers={"X-Arthor-Signature": "sha256=" + ("0" * 64)},
        )
    assert resp.status_code == 401, (
        f"AC-3: must 401 on bad signature, got {resp.status_code}"
    )
    assert resp.json().get("detail") == "invalid_signature", (
        "AC-3: detail must be 'invalid_signature' on bad signature"
    )


@pytest.mark.asyncio
async def test_require_hmac_200_on_valid_sig_caches_raw_body():
    try:
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app.auth.hmac.sign_body must be importable: {exc}")

    app, ASGITransport, AsyncClient = _build_app(secret="k")
    body = b"hello"
    sig = sign_body("k", body)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/echo", content=body, headers={"X-Arthor-Signature": sig}
        )
    assert resp.status_code == 200, (
        f"AC-3: must 200 on valid signature, got {resp.status_code} {resp.text!r}"
    )
    payload = resp.json()
    assert payload["len"] == len(body), "AC-3: dependency must return the raw body bytes"
    assert payload["raw_body_seen"] is True, (
        "AC-3: require_hmac must cache the raw body on request.state.raw_body"
    )
