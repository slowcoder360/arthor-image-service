"""s14 AC-6: POST /inspector/assets/{asset_id}/soft-delete without `reason` → 400."""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_soft_delete_missing_reason_returns_400(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    asset_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        get_login = await client.get("/inspector/login")
        csrf = get_login.cookies.get("arthor_csrf_token") or ""
        client.cookies.set("arthor_csrf_token", csrf)
        resp = await client.post(
            f"/inspector/assets/{asset_id}/soft-delete",
            data={"csrf_token": csrf},
            headers={"Authorization": "Bearer secret-admin-token"},
        )
    assert resp.status_code == 400, (
        f"AC-6: soft-delete without reason must 400; got {resp.status_code}"
    )
