"""s03 AC-5: issue_inspector_cookie sets HttpOnly+Secure+SameSite=Strict, max_age=86400."""

from __future__ import annotations

import pytest


def _import_issuer():
    try:
        from app.auth.inspector_token import issue_inspector_cookie  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-5: `app.auth.inspector_token.issue_inspector_cookie` must be importable ({exc})"
        )
    return issue_inspector_cookie


@pytest.mark.asyncio
async def test_issue_inspector_cookie_attributes_via_route():
    try:
        from fastapi import FastAPI, Response
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"fastapi/httpx not installed: {exc}")

    issue_inspector_cookie = _import_issuer()
    app = FastAPI()

    @app.post("/login")
    async def _login(response: Response):
        issue_inspector_cookie(response, "secret-token")
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/login")

    set_cookie = resp.headers.get("set-cookie", "")
    assert "arthor_inspector_token" in set_cookie, (
        "AC-5: Set-Cookie must include 'arthor_inspector_token'"
    )
    lower = set_cookie.lower()
    assert "httponly" in lower, "AC-5: cookie must be HttpOnly"
    assert "secure" in lower, "AC-5: cookie must be Secure"
    assert "samesite=strict" in lower, "AC-5: cookie must be SameSite=Strict"
    assert "max-age=86400" in lower, "AC-5: cookie must have max_age=86400"
