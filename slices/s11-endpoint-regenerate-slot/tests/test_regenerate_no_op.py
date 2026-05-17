"""s11 AC-3: both `new_seed` and `new_prompt_modifier` missing → 400 (no-op)."""

from __future__ import annotations

import json
import os
import uuid

import pytest

from _s11_helpers import build_payload, cleanup_run, seed_prior_pack_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_regenerate_no_op_returns_400(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app + sign_body + asyncpg must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    payload = build_payload()
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    try:
        async with pool.acquire() as conn:
            run_id, asset_id = await seed_prior_pack_run(conn, payload)

        body = {"asset_id": str(asset_id), "new_seed": None, "new_prompt_modifier": None}
        raw = json.dumps(body).encode()
        sig = sign_body("k", raw)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/images/regenerate-slot",
                content=raw,
                headers={"X-Arthor-Signature": sig},
            )
        assert resp.status_code == 400, (
            f"AC-3: regenerate with both new_seed and new_prompt_modifier omitted "
            f"must 400 (no-op); got {resp.status_code} {resp.text!r}"
        )
    finally:
        async with pool.acquire() as conn:
            await cleanup_run(conn, run_id)
        await pool.close()
