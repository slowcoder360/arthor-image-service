"""s12 AC-3 + AC-6 + AC-7: valid signed POST returns 200 with the documented
body shape; an agent_runs row with run_type='image_style_preview' exists; one
external_media_assets row with metadata.slot_id='style_profile_preview' exists.
"""

from __future__ import annotations

import json
import os

import pytest

from _s12_helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_preview_happy_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3/6/7: app + sign_body + asyncpg must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    payload = build_payload()
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    run_id = None
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", timeout=60.0
        ) as client:
            resp = await client.post(
                "/images/style-profile/preview",
                content=raw,
                headers={"X-Arthor-Signature": sig},
            )
        assert resp.status_code == 200, (
            f"AC-7: synchronous preview must 200; got {resp.status_code} {resp.text!r}"
        )
        body = resp.json()
        for field in (
            "agent_run_id",
            "asset_id",
            "r2_url",
            "prompt_hash",
            "cost_cents",
            "latency_ms",
        ):
            assert field in body, f"AC-7: response body missing required field {field!r}"
        run_id = body["agent_run_id"]

        async with pool.acquire() as conn:
            run_row = await conn.fetchrow(
                "SELECT run_type FROM agent_runs WHERE id = $1", run_id
            )
            assert run_row is not None and run_row["run_type"] == "image_style_preview", (
                f"AC-3: agent_runs row must have run_type='image_style_preview'; "
                f"got {run_row and run_row['run_type']!r}"
            )
            ema_meta = await conn.fetchval(
                """
                SELECT metadata FROM external_media_assets
                WHERE agent_run_id = $1
                """,
                run_id,
            )
        if isinstance(ema_meta, str):
            ema_meta = json.loads(ema_meta)
        assert ema_meta and ema_meta.get("slot_id") == "style_profile_preview", (
            f"AC-6: external_media_assets row must have metadata.slot_id='style_profile_preview'; "
            f"got {ema_meta and ema_meta.get('slot_id')!r}"
        )
    finally:
        if run_id is not None:
            async with pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
                )
                await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
                await conn.execute(
                    "DELETE FROM image_request_payloads WHERE agent_run_id = $1", run_id
                )
                await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
        await pool.close()
