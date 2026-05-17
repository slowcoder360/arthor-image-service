"""s13 AC-10: GET /inspector/static/htmx.min.js → 200; same for inspector.css."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_static_assets_are_mounted(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-10: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        htmx = await client.get("/inspector/static/htmx.min.js")
        css = await client.get("/inspector/static/inspector.css")

    assert htmx.status_code == 200, (
        f"AC-10: /inspector/static/htmx.min.js must 200; got {htmx.status_code}"
    )
    assert css.status_code == 200, (
        f"AC-10: /inspector/static/inspector.css must 200; got {css.status_code}"
    )
