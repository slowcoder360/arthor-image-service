"""s13 AC-2: POST /inspector/login — valid token redirects + sets cookie;
invalid token renders the form with an error.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_login_post_valid_token_sets_cookie(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=False
    ) as client:
        # First GET to obtain the csrf cookie + form token from the login page.
        get_resp = await client.get("/inspector/login")
        assert get_resp.status_code == 200, (
            f"AC-2: GET /inspector/login must 200; got {get_resp.status_code}"
        )
        csrf = get_resp.cookies.get("arthor_csrf_token")
        ok = await client.post(
            "/inspector/login",
            data={"token": "secret-admin-token", "csrf_token": csrf or ""},
        )
        bad = await client.post(
            "/inspector/login",
            data={"token": "wrong", "csrf_token": csrf or ""},
        )

    assert ok.status_code in (302, 303), (
        f"AC-2: valid login must redirect (302/303); got {ok.status_code}"
    )
    assert "set-cookie" in {k.lower() for k in ok.headers.keys()}, (
        "AC-2: valid login must Set-Cookie"
    )
    assert bad.status_code == 200, (
        f"AC-2: invalid token must re-render form with 200; got {bad.status_code}"
    )
    body = bad.text.lower()
    assert "error" in body or "invalid" in body, (
        f"AC-2: invalid-token response body must contain an error message; got {body[:200]!r}"
    )
