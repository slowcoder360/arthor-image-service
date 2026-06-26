"""s19 AC-4: the decision is recorded for both corpus and live generation modes."""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_decision_recorded_in_corpus_mode(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, _, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = build_hero_request(industry="dental", idempotency_key=f"s19-corpus-{uuid.uuid4()}")
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )
    run_id = uuid.UUID(resp.json()["agent_run_id"])
    assert "hero_layout_decision" in pool.store.agent_runs[run_id]["metadata"], (
        "AC-4: corpus-mode runs must record hero_layout_decision"
    )


@pytest.mark.asyncio
async def test_decision_recorded_in_live_mode(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, _, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    import app.routes.hero_candidates as hero_routes
    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    async def _noop_worker(*args, **kwargs):
        return None

    monkeypatch.setattr(hero_routes, "run_hero_candidates_in_background", _noop_worker)

    payload = build_hero_request(industry="dental", idempotency_key=f"s19-live-{uuid.uuid4()}")
    payload["generation_mode"] = "live"
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )
    run_id = uuid.UUID(resp.json()["agent_run_id"])
    assert "hero_layout_decision" in pool.store.agent_runs[run_id]["metadata"], (
        "AC-4: live-mode runs must also record hero_layout_decision"
    )
