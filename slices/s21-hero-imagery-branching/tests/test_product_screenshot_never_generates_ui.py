"""s21 AC-5: product_screenshot with no client capture falls back to abstract — never synthesizes UI."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_product_screenshot_falls_back_to_abstract(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, _, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    import app.routes.hero_candidates as hero_routes
    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    async def _noop_worker(*args, **kwargs):
        return None

    monkeypatch.setattr(hero_routes, "run_hero_candidates_in_background", _noop_worker)

    payload = build_hero_request(
        industry="b2b software",
        brand_mode="tech_saas",
        generation_mode="live",
        idempotency_key=f"s21-prodshot-{uuid.uuid4()}",
    )
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )
    assert resp.status_code in (202, 200), f"unexpected status {resp.status_code}: {resp.text}"
    run_id = uuid.UUID(resp.json()["agent_run_id"])

    meta = pool.store.agent_runs[run_id]["metadata"]
    hero_imagery = meta.get("hero_imagery") or {}
    assert hero_imagery.get("kind") == "abstract", (
        "AC-5: product_screenshot without a client capture must fall back to abstract imagery"
    )
    # The generated prompt must never instruct a synthetic product UI / screenshot.
    prompt = (hero_imagery.get("prompt") or "").lower()
    assert "screenshot" not in prompt and "ui mockup" not in prompt and "user interface" not in prompt, (
        "AC-5: the service must never construct a synthetic product-screenshot prompt"
    )
