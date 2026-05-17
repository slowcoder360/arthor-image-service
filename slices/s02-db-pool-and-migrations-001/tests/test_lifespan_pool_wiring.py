"""s02 AC-2: lifespan attaches services.pool when DATABASE_URL is set; warns + None when not."""

from __future__ import annotations

import logging
import os

import pytest


@pytest.mark.asyncio
async def test_lifespan_leaves_pool_none_when_database_url_unset(
    monkeypatch, tmp_path, caplog
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: app.main.app must be importable ({exc})")

    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx is not installed: {exc}")

    caplog.set_level(logging.WARNING)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.get("/healthz")
        services = getattr(app.state, "services", None)
        assert services is not None, "AC-2: services must be attached to app.state"
        assert getattr(services, "pool", "MISSING") is None, (
            "AC-2: services.pool must be None when DATABASE_URL is unset"
        )

    warned = any(
        "database_url" in rec.getMessage().lower() for rec in caplog.records
    )
    assert warned, (
        "AC-2: lifespan must log a warning when DATABASE_URL is unset"
    )


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_lifespan_attaches_pool_when_database_url_set(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: app.main.app must be importable ({exc})")
    try:
        import asyncpg
    except ImportError as exc:
        pytest.fail(f"asyncpg is not installed: {exc}")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx is not installed: {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        await client.get("/healthz")
        services = getattr(app.state, "services", None)
        assert services is not None, "AC-2: services must be attached to app.state"
        assert isinstance(services.pool, asyncpg.Pool), (
            "AC-2: services.pool must be an asyncpg.Pool when DATABASE_URL is set"
        )
