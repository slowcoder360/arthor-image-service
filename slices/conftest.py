"""Orchestrator-owned conftest for the red suite.

Registers the `requires_db` and `requires_r2` markers and skips marked
tests when the corresponding environment is unavailable. This file is a
shim for the tests-first phase only; once s01 ships, the canonical
`tests/conftest.py` it creates also registers these markers and the two
declarations coexist harmlessly.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Ensure integration tests that hit `app.main:app` see auth secrets unless overridden.
os.environ.setdefault("FASTAPI_ARTHOR_SHARED_SECRET", "test-hmac-secret")
os.environ.setdefault("INSPECTOR_ADMIN_TOKEN", "test-inspector-token")


REQUIRES_DB_ENV = "DATABASE_URL"
REQUIRES_R2_ENVS = ("R2_ENDPOINT_URL", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


@pytest.fixture(autouse=True)
def _restore_env_and_app_state_after_each_test() -> None:
    """s01 settings tests delete env vars; shared `app.main.app` must not keep stale RuntimeServices."""
    yield
    os.environ.setdefault("FASTAPI_ARTHOR_SHARED_SECRET", "test-hmac-secret")
    os.environ.setdefault("INSPECTOR_ADMIN_TOKEN", "test-inspector-token")
    try:
        import app.main as app_main

        if hasattr(app_main.app.state, "services"):
            delattr(app_main.app.state, "services")
        app_main._missing_database_url_logged = False
        app_main._missing_r2_config_logged = False
    except Exception:
        pass
    try:
        from app.config import get_settings

        get_settings.cache_clear()
    except Exception:
        pass


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_db: test requires a Postgres DSN in DATABASE_URL; skipped otherwise.",
    )
    config.addinivalue_line(
        "markers",
        "requires_r2: test requires R2_* envs (typically mocked via moto[s3]); skipped otherwise.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not os.getenv(REQUIRES_DB_ENV):
        skip_db = pytest.mark.skip(reason=f"{REQUIRES_DB_ENV} unset")
        for item in items:
            if "requires_db" in item.keywords:
                item.add_marker(skip_db)

    if not all(os.getenv(name) for name in REQUIRES_R2_ENVS):
        skip_r2 = pytest.mark.skip(
            reason=f"R2_* envs unset (need {', '.join(REQUIRES_R2_ENVS)})"
        )
        for item in items:
            if "requires_r2" in item.keywords:
                item.add_marker(skip_r2)
