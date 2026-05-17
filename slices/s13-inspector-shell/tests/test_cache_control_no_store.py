"""s13 AC-11: every inspector HTML response sets `Cache-Control: no-store`."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_inspector_html_sets_cache_control_no_store(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-11: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login = await client.get("/inspector/login")
        runs = await client.get(
            "/inspector/runs",
            headers={"Authorization": "Bearer secret-admin-token"},
        )

    assert login.headers.get("cache-control", "").lower() == "no-store", (
        f"AC-11: /inspector/login Cache-Control must be 'no-store'; "
        f"got {login.headers.get('cache-control')!r}"
    )
    assert runs.headers.get("cache-control", "").lower() == "no-store", (
        f"AC-11: /inspector/runs Cache-Control must be 'no-store'; "
        f"got {runs.headers.get('cache-control')!r}"
    )
