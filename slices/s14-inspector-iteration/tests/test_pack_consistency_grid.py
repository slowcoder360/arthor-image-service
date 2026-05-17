"""s14 AC-4: GET /inspector/runs/{id}/grid returns HTML with the documented
CSS grid container and all uploaded slot thumbnails.
"""

from __future__ import annotations

import os

import pytest

from _s14_db_helpers import cleanup_run, make_pool, seed_uploaded_asset


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_pack_consistency_grid_renders_thumbnails(monkeypatch, tmp_path):
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
    run_id = None
    asset_ids: list = []
    try:
        async with pool.acquire() as conn:
            run_id, aid1 = await seed_uploaded_asset(conn, slot_id="s-0")
            site_row = await conn.fetchrow(
                "SELECT site_id FROM agent_runs WHERE id = $1", run_id
            )
            import uuid as _uuid
            import json as _json
            aid2 = _uuid.uuid4()
            await conn.execute(
                """
                INSERT INTO external_media_assets
                  (id, provider, status, agent_run_id, site_id, metadata, r2_url)
                VALUES ($1, 'openai_image', 'uploaded', $2, $3, $4::jsonb, $5)
                """,
                aid2,
                run_id,
                site_row["site_id"],
                _json.dumps({"slot_id": "s-1", "seed": 101, "prompt_hash": "h1"}),
                f"https://r2.example.com/{aid2}.png",
            )
            asset_ids = [aid1, aid2]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                f"/inspector/runs/{run_id}/grid",
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-4: grid partial must 200; got {resp.status_code}"
        )
        body = resp.text
        assert "repeat(auto-fill, minmax(256px, 1fr))" in body, (
            "AC-4: HTML must include the documented grid-template-columns CSS"
        )
        for aid in asset_ids:
            assert str(aid) in body, (
                f"AC-4: grid HTML must include thumbnail for asset {aid}"
            )
    finally:
        async with pool.acquire() as conn:
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
