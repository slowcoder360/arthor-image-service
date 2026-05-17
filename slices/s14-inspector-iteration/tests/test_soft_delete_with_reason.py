"""s14 AC-6: POST /inspector/assets/{asset_id}/soft-delete with a reason
transitions the asset to `superseded` with `metadata.soft_deleted = true`
and `metadata.soft_delete_reason = <reason>`.
"""

from __future__ import annotations

import json
import os

import pytest

from _s14_db_helpers import cleanup_run, make_pool, seed_uploaded_asset


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_soft_delete_with_reason_marks_metadata(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: app.main.app must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    reason = "off-brand color palette"
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
                f"/inspector/assets/{asset_id}/soft-delete",
                data={"reason": reason, "csrf_token": csrf},
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-6: soft-delete with reason must 200; got {resp.status_code}"
        )
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status, metadata FROM external_media_assets WHERE id = $1",
                asset_id,
            )
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        assert row["status"] == "superseded", (
            f"AC-6: soft-delete must transition status to 'superseded'; got {row['status']!r}"
        )
        assert meta.get("soft_deleted") is True, (
            f"AC-6: metadata.soft_deleted must be true; got {meta!r}"
        )
        assert meta.get("soft_delete_reason") == reason, (
            f"AC-6: metadata.soft_delete_reason must equal {reason!r}; "
            f"got {meta.get('soft_delete_reason')!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
