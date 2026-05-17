"""s01 AC-5: GET /healthz must return 200 + the documented JSON body."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_healthz_returns_documented_body():
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: `app.main.app` must be importable to call /healthz ({exc})")

    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx is not installed in the test environment: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/healthz")

    assert response.status_code == 200, (
        f"AC-5: GET /healthz must return 200, got {response.status_code}"
    )
    body = response.json()
    assert body == {
        "status": "ok",
        "service": "arthor-image-service",
        "version": "0.1.0",
    }, (
        "AC-5: GET /healthz body must equal "
        "{'status': 'ok', 'service': 'arthor-image-service', 'version': '0.1.0'}"
    )
