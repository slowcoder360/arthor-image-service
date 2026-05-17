"""s13 AC-4: `?run_type=...` filters the list against the allow-list.
`?run_type=bogus` → 400.
"""

from __future__ import annotations

import os

import pytest

from _s13_db_helpers import cleanup_run, make_pool, seed_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_runs_list_filter_run_type(monkeypatch, tmp_path):
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
    pack_id = None
    preview_id = None
    try:
        async with pool.acquire() as conn:
            pack_id, _ = await seed_run(conn, run_type="image_pack_generation")
            preview_id, _ = await seed_run(conn, run_type="image_style_preview")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            filtered = await client.get(
                "/inspector/runs",
                params={"run_type": "image_pack_generation"},
                headers={"Authorization": "Bearer secret-admin-token"},
            )
            bogus = await client.get(
                "/inspector/runs",
                params={"run_type": "bogus"},
                headers={"Authorization": "Bearer secret-admin-token"},
            )

        assert filtered.status_code == 200, (
            f"AC-4: filtered list must 200; got {filtered.status_code}"
        )
        assert str(pack_id) in filtered.text, (
            "AC-4: filtered list must include the image_pack_generation run"
        )
        assert str(preview_id) not in filtered.text, (
            "AC-4: filtered list must NOT include the image_style_preview run when filtering on image_pack_generation"
        )
        assert bogus.status_code == 400, (
            f"AC-4: unknown run_type must 400; got {bogus.status_code}"
        )
    finally:
        async with pool.acquire() as conn:
            if pack_id is not None:
                await cleanup_run(conn, pack_id)
            if preview_id is not None:
                await cleanup_run(conn, preview_id)
        await pool.close()
