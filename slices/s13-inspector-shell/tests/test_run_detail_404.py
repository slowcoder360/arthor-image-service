"""s13 AC-5: unknown run id → 404."""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_run_detail_unknown_id_returns_404(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(
            f"/inspector/runs/{uuid.uuid4()}",
            headers={"Authorization": "Bearer secret-admin-token"},
        )
    assert resp.status_code == 404, (
        f"AC-5: unknown run id must 404; got {resp.status_code}"
    )
