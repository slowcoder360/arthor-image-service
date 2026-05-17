"""s13 AC-5: GET /inspector/runs/{id} renders payload + style profile +
assets + tool_calls + costs.
"""

from __future__ import annotations

import os

import pytest

from _s13_db_helpers import cleanup_run, make_pool, seed_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_run_detail_renders_full_view(monkeypatch, tmp_path):
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
            run_id, asset_ids = await seed_run(
                conn,
                payload={
                    "payload_version": "1.0",
                    "marker": "PAYLOAD_MARKER_XYZ",
                },
                style_profile={"lighting": "STYLE_MARKER_LIGHTING"},
                asset_count=2,
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                f"/inspector/runs/{run_id}",
                headers={"Authorization": "Bearer secret-admin-token"},
            )
        assert resp.status_code == 200, (
            f"AC-5: detail must 200; got {resp.status_code} {resp.text[:200]!r}"
        )
        body = resp.text
        assert "PAYLOAD_MARKER_XYZ" in body, "AC-5: HTML must render the payload"
        assert "STYLE_MARKER_LIGHTING" in body, (
            "AC-5: HTML must render the resolved style profile"
        )
        for aid in asset_ids:
            assert str(aid) in body, (
                f"AC-5: HTML must render every asset row (missing {aid})"
            )
        assert "openai_image" in body, (
            "AC-5: HTML must render the tool_calls provider name"
        )
        assert "0.12" in body or "$0.12" in body or "12" in body, (
            "AC-5: HTML must render the cost (12 cents or $0.12)"
        )
    finally:
        async with pool.acquire() as conn:
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
