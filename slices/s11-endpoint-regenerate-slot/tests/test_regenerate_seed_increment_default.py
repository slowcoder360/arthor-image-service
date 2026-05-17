"""s11 AC-5: when `new_seed` is omitted, the route uses `original_seed + 1`.

Exercises the route via HTTP. Captures the seed the worker receives by
monkeypatching `pack_worker.run_single_slot_in_background` to record its args.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest

from _s11_helpers import build_payload, cleanup_run, seed_prior_pack_run


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_regenerate_default_seed_is_original_plus_one(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
        from app.orchestration import pack_worker  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: app + sign_body + pack_worker must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    captured: dict = {}

    async def _capture(services, **kwargs):
        captured["kwargs"] = kwargs

    monkeypatch.setattr(pack_worker, "run_single_slot_in_background", _capture)

    payload = build_payload()
    original_seed = 100
    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    new_run_id = None
    old_run_id = None
    try:
        async with pool.acquire() as conn:
            old_run_id, old_asset_id = await seed_prior_pack_run(
                conn, payload, seed=original_seed
            )

        body = {"asset_id": str(old_asset_id)}  # new_seed omitted, new_prompt_modifier provided to bypass no-op
        body["new_prompt_modifier"] = "any modifier"
        raw = json.dumps(body).encode()
        sig = sign_body("k", raw)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/images/regenerate-slot",
                content=raw,
                headers={"X-Arthor-Signature": sig},
            )
        assert resp.status_code == 202, (
            f"AC-5: regenerate without new_seed must 202; got "
            f"{resp.status_code} {resp.text!r}"
        )
        new_run_id = uuid.UUID(resp.json()["agent_run_id"])

        assert "kwargs" in captured, (
            "AC-5: route must invoke pack_worker.run_single_slot_in_background"
        )
        seed = captured["kwargs"].get("seed")
        assert seed == original_seed + 1, (
            f"AC-5: when new_seed is omitted, worker must receive original_seed+1 "
            f"({original_seed + 1}); got {seed!r}"
        )
    finally:
        async with pool.acquire() as conn:
            if new_run_id is not None:
                await cleanup_run(conn, new_run_id)
            if old_run_id is not None:
                await cleanup_run(conn, old_run_id)
        await pool.close()
