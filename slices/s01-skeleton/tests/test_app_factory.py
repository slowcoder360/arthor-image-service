"""s01 AC-2 / AC-5: FastAPI app instance, title, and /healthz route registration."""

from __future__ import annotations

import pytest


def _import_app():
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-2: `app.main.app` must be importable; module not yet implemented ({exc})"
        )
    return app


def test_app_is_fastapi_instance():
    app = _import_app()
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        pytest.fail(f"fastapi is not installed in the test environment: {exc}")
    assert isinstance(
        app, FastAPI
    ), "AC-2: `app.main.app` must be an instance of fastapi.FastAPI"


def test_app_title_matches_adr_0002():
    app = _import_app()
    assert (
        app.title == "arthor-image-service v1"
    ), "AC-2: FastAPI app title must equal 'arthor-image-service v1' (ADR-0002)"


def test_healthz_route_registered():
    app = _import_app()
    paths = {getattr(route, "path", None) for route in app.routes}
    assert (
        "/healthz" in paths
    ), "AC-5: GET /healthz route must be registered on the app at module import time"


def test_app_has_lifespan_configured():
    app = _import_app()
    lifespan = getattr(app.router, "lifespan_context", None)
    assert (
        lifespan is not None
    ), "AC-2: `app.main.app` must be constructed with a lifespan context manager (ADR-0002)"
