"""s13 AC-1: `/inspector/runs` requires auth → 401; `/inspector/login` is open → 200."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_inspector_runs_requires_auth(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        runs = await client.get("/inspector/runs")
        login = await client.get("/inspector/login")

    assert runs.status_code == 401, (
        f"AC-1: unauthenticated GET /inspector/runs must 401; got {runs.status_code}"
    )
    assert login.status_code == 200, (
        f"AC-1: GET /inspector/login must 200 (auth not required); got {login.status_code}"
    )
