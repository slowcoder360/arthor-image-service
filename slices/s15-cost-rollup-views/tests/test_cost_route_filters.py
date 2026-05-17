"""s15 AC-3: `?date_from=...&site_id=...&provider=...` constrains all five
rollups. Rows for filtered-out site_id are absent from the rendered HTML.
"""

from __future__ import annotations

import os
import uuid

import pytest

from _s15_db_helpers import cleanup_run, make_pool, seed_run_with_cost


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_cost_route_filters_by_site(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    pool = await make_pool()
    site_a = uuid.uuid4()
    site_b = uuid.uuid4()
    run_a = None
    run_b = None
    try:
        async with pool.acquire() as conn:
            run_a = await seed_run_with_cost(conn, cost_cents=111, site_id=site_a)
            run_b = await seed_run_with_cost(conn, cost_cents=222, site_id=site_b)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                "/inspector/cost",
                params={"site_id": str(site_a)},
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-3: filter request must 200; got {resp.status_code}"
        )
        body = resp.text
        assert str(site_a) in body, (
            "AC-3: filtered output must include the filtered-on site_id"
        )
        assert str(site_b) not in body, (
            "AC-3: filtered output must NOT include rows for other sites"
        )
    finally:
        async with pool.acquire() as conn:
            if run_a is not None:
                await cleanup_run(conn, run_a)
            if run_b is not None:
                await cleanup_run(conn, run_b)
        await pool.close()
