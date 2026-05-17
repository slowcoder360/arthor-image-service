"""s14 AC-5: POST /inspector/assets/{asset_id}/unsupersede against an `uploaded`
asset → 400 (cannot unsupersede something that wasn't superseded).
"""

from __future__ import annotations

import os

import pytest

from _s14_db_helpers import cleanup_run, make_pool, seed_uploaded_asset


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_unsupersede_rejects_uploaded_asset(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    pool = await make_pool()
    run_id = None
    try:
        async with pool.acquire() as conn:
            run_id, asset_id = await seed_uploaded_asset(conn)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            get_login = await client.get("/inspector/login")
            csrf = get_login.cookies.get("arthor_csrf_token") or ""
            client.cookies.set("arthor_csrf_token", csrf)
            resp = await client.post(
                f"/inspector/assets/{asset_id}/unsupersede",
                data={"csrf_token": csrf},
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 400, (
            f"AC-5: unsupersede of an uploaded asset must 400; "
            f"got {resp.status_code} {resp.text[:200]!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
