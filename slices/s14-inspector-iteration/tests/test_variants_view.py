"""s14 AC-3: GET /inspector/slots/{slot_id}/variants?run_id=... returns HTML
with every variant for the slot in order, each showing prompt_hash, seed,
provider, cost.
"""

from __future__ import annotations

import os

import pytest

from _s14_db_helpers import cleanup_run, make_pool, seed_uploaded_asset, supersede_asset_row
import uuid


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_variants_view_renders_history_for_slot(monkeypatch, tmp_path):
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
    run_id = None
    new_run_id = None
    try:
        async with pool.acquire() as conn:
            run_id, old_asset_id = await seed_uploaded_asset(conn, slot_id="s-0", seed=100, prompt_hash="hashA")
            new_run_id = uuid.uuid4()
            new_asset_id = uuid.uuid4()
            site_row = await conn.fetchrow(
                "SELECT site_id FROM agent_runs WHERE id = $1", run_id
            )
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
            resp = await client.get(
                "/inspector/slots/s-0/variants",
                params={"run_id": str(run_id)},
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-3: variants partial must 200; got {resp.status_code}"
        )
        body = resp.text
        assert "hashA" in body, "AC-3: HTML must render the old variant prompt_hash"
        assert "100" in body, "AC-3: HTML must render the old seed value"
        assert "openai_image" in body, "AC-3: HTML must render the provider name"
    finally:
        async with pool.acquire() as conn:
            if new_run_id is not None:
                await cleanup_run(conn, new_run_id)
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
