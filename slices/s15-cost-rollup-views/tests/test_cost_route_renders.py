"""s15 AC-2: GET /inspector/cost (authed) → 200 + HTML containing all five
rollup table headers.
"""

from __future__ import annotations

import os

import pytest

from _s15_db_helpers import cleanup_run, make_pool, seed_run_with_cost


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_cost_route_renders_all_five_tables(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    pool = await make_pool()
    run_id = None
    try:
        async with pool.acquire() as conn:
            run_id = await seed_run_with_cost(conn, cost_cents=42)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                "/inspector/cost",
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-2: GET /inspector/cost authed must 200; got {resp.status_code}"
        )
        body = resp.text.lower()
        for needle in ("per run", "per day", "per site", "per provider", "per slot"):
            assert needle in body, (
                f"AC-2: HTML must contain rollup table header {needle!r}"
            )
    finally:
        async with pool.acquire() as conn:
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
