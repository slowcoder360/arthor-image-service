"""s01 AC-2: lifespan attaches services to app.state and tears down without errors."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_lifespan_attaches_services_and_tears_down(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-2: `app.main.app` must be importable to exercise its lifespan ({exc})"
        )

    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx is not installed in the test environment: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.get("/healthz")
        services = getattr(app.state, "services", None)
        assert services is not None, (
            "AC-2: lifespan must attach `services` to app.state during startup"
        )
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]

        assert isinstance(services, RuntimeServices), (
            "AC-2: app.state.services must be a RuntimeServices instance"
        )
