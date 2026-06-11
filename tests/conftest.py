"""Shared pytest configuration for arthor-image-service and slice suites."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


REQUIRES_DB_ENV = "DATABASE_URL"
def _r2_configured() -> bool:
    access = os.getenv("R2_ACCESS_KEY_ID")
    secret = os.getenv("R2_SECRET_ACCESS_KEY")
    bucket = os.getenv("R2_BUCKET") or os.getenv("R2_BUCKET_NAME")
    endpoint = os.getenv("R2_ENDPOINT_URL")
    account = os.getenv("R2_ACCOUNT_ID")
    return bool(access and secret and bucket and (endpoint or account))


REQUIRES_R2_ENVS = (
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "(R2_BUCKET or R2_BUCKET_NAME)",
    "(R2_ENDPOINT_URL or R2_ACCOUNT_ID)",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_db: test requires a Postgres DSN in DATABASE_URL; skipped otherwise.",
    )
    config.addinivalue_line(
        "markers",
        (
            "requires_r2: test requires R2_* envs "
            "(typically mocked via moto[s3]); skipped otherwise."
        ),
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not os.getenv(REQUIRES_DB_ENV):
        skip_db = pytest.mark.skip(reason=f"{REQUIRES_DB_ENV} unset")
        for item in items:
            if "requires_db" in item.keywords:
                item.add_marker(skip_db)

    if not _r2_configured():
        skip_r2 = pytest.mark.skip(
            reason="R2 envs unset (need access key, secret, bucket name, endpoint or account id)"
        )
        for item in items:
            if "requires_r2" in item.keywords:
                item.add_marker(skip_r2)


@pytest.fixture
async def app_client():
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        yield client
