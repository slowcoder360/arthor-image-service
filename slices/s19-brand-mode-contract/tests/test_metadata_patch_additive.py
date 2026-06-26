"""s19 AC-6: hero_layout_decision is additive — existing metadata keys are preserved."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app

PRESERVED_KEYS = ("style_profile", "hero_visual_strategy", "generation_mode", "hero_viewport")


@pytest.mark.asyncio
async def test_existing_metadata_keys_preserved(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, _, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = build_hero_request(industry="dental", idempotency_key=f"s19-additive-{uuid.uuid4()}")
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )
    run_id = uuid.UUID(resp.json()["agent_run_id"])
    meta = pool.store.agent_runs[run_id]["metadata"]

    for key in PRESERVED_KEYS:
        assert key in meta, (
            f"AC-6: adding hero_layout_decision must not drop existing metadata key {key!r}"
        )
    assert "hero_layout_decision" in meta, "AC-3: hero_layout_decision must be present"
