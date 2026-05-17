"""s14 AC-5: POST /inspector/assets/{asset_id}/unsupersede on a superseded
asset transitions it back to 'uploaded' and re-renders the variants panel.
"""

from __future__ import annotations

import os
import uuid

import pytest

from _s14_db_helpers import cleanup_run, make_pool, seed_uploaded_asset, supersede_asset_row


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_unsupersede_happy_path(monkeypatch, tmp_path):
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
    new_run_id = None
    try:
        async with pool.acquire() as conn:
            run_id, old_asset_id = await seed_uploaded_asset(conn, slot_id="s-0")
            site_row = await conn.fetchrow(
                "SELECT site_id FROM agent_runs WHERE id = $1", run_id
            )
            new_run_id = uuid.uuid4()
            new_asset_id = uuid.uuid4()
            await supersede_asset_row(
                conn,
                old_asset_id=old_asset_id,
                new_asset_id=new_asset_id,
                new_run_id=new_run_id,
                site_id=site_row["site_id"],
                slot_id="s-0",
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            get_login = await client.get("/inspector/login")
            csrf = get_login.cookies.get("arthor_csrf_token") or ""
            client.cookies.set("arthor_csrf_token", csrf)
            resp = await client.post(
                f"/inspector/assets/{old_asset_id}/unsupersede",
                data={"csrf_token": csrf},
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-5: unsupersede must 200; got {resp.status_code} {resp.text[:200]!r}"
        )
        async with pool.acquire() as conn:
            new_status = await conn.fetchval(
                "SELECT status FROM external_media_assets WHERE id = $1",
                old_asset_id,
            )
        assert new_status == "uploaded", (
            f"AC-5: unsuperseded asset must transition to 'uploaded'; got {new_status!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if new_run_id is not None:
                await cleanup_run(conn, new_run_id)
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
