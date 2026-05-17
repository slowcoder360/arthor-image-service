"""s13 AC-4: authed GET /inspector/runs returns HTML containing a table row
per run, pagination links, and the filter form.
"""

from __future__ import annotations

import os

import pytest

from _s13_db_helpers import cleanup_run, make_pool, seed_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_runs_list_renders_table_and_pagination(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    pool = await make_pool()
    seeded_ids: list = []
    try:
        async with pool.acquire() as conn:
            for _ in range(3):
                rid, _ = await seed_run(conn)
                seeded_ids.append(rid)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                "/inspector/runs",
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-4: authed list must 200; got {resp.status_code} {resp.text[:200]!r}"
        )
        body = resp.text
        for rid in seeded_ids:
            assert str(rid) in body, (
                f"AC-4: rendered HTML must contain seeded run id {rid}"
            )
        assert "<table" in body.lower(), "AC-4: HTML must contain a <table> element"
        assert "page" in body.lower(), "AC-4: HTML must contain pagination links"
        assert "<form" in body.lower(), "AC-4: HTML must contain a filter form"
    finally:
        async with pool.acquire() as conn:
            for rid in seeded_ids:
                await cleanup_run(conn, rid)
        await pool.close()
