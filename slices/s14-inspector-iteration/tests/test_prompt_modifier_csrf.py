"""s14 AC-9: POST /inspector/slots/{asset_id}/regenerate without csrf_token → 403."""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_prompt_modifier_csrf_protection(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-9: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    asset_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            f"/inspector/slots/{asset_id}/regenerate",
            data={"prompt_modifier": "x"},
            headers={"Authorization": "Bearer secret-admin-token"},
        )
    assert resp.status_code == 403, (
        f"AC-9: POST without csrf_token must 403; got {resp.status_code}"
    )
