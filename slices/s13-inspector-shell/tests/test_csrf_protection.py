"""s13 AC-3: inspector POSTs are CSRF-protected (double-submit cookie pattern).
Missing or mismatched csrf_token → 403; matched → no 403.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_inspector_csrf_protection(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=False
    ) as client:
        get_resp = await client.get("/inspector/login")
        csrf_cookie = get_resp.cookies.get("arthor_csrf_token")

        # 1. No csrf_token form field → 403
        no_form = await client.post(
            "/inspector/login",
            data={"token": "secret-admin-token"},
        )
        # 2. Mismatched form vs cookie → 403
        client.cookies.set("arthor_csrf_token", csrf_cookie or "cookieval")
        mismatched = await client.post(
            "/inspector/login",
            data={"token": "secret-admin-token", "csrf_token": "not-the-cookie"},
        )
        # 3. Matched form == cookie → not 403
        matched = await client.post(
            "/inspector/login",
            data={"token": "secret-admin-token", "csrf_token": csrf_cookie or "cookieval"},
        )

    assert no_form.status_code == 403, (
        f"AC-3: POST without csrf_token must 403; got {no_form.status_code}"
    )
    assert mismatched.status_code == 403, (
        f"AC-3: POST with mismatched csrf_token vs cookie must 403; got {mismatched.status_code}"
    )
    assert matched.status_code != 403, (
        f"AC-3: POST with matched csrf must not 403; got {matched.status_code}"
    )
