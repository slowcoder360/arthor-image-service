"""s13 AC-5: asset with `metadata.palette_drift = true` → palette-drift badge in HTML."""

from __future__ import annotations

import os

import pytest

from _s13_db_helpers import cleanup_run, make_pool, seed_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_run_detail_renders_palette_drift_badge(monkeypatch, tmp_path):
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
            run_id, _ = await seed_run(conn, palette_drift=True, asset_count=1)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                f"/inspector/runs/{run_id}",
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-5: detail must 200; got {resp.status_code} {resp.text[:200]!r}"
        )
        body = resp.text.lower()
        assert "palette" in body and "drift" in body, (
            f"AC-5: palette-drift badge must appear in HTML; "
            f"got body slice {body[:400]!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
