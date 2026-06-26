"""s21 AC-5: a supplied client capture is recorded as the hero asset, with no generation."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_client_capture_recorded_without_generation(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, fake, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    import app.routes.hero_candidates as hero_routes
    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    async def _noop_worker(*args, **kwargs):
        return None

    monkeypatch.setattr(hero_routes, "run_hero_candidates_in_background", _noop_worker)

    # The client capture field is additive in s21; sending it must be accepted, not 400.
    payload = build_hero_request(
        industry="b2b software",
        brand_mode="tech_saas",
        generation_mode="live",
        product_capture_url="https://cdn.example/app-shot.png",
        idempotency_key=f"s21-capture-{uuid.uuid4()}",
    )
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )
    assert resp.status_code in (202, 200), (
        f"AC-5: the additive product_capture_url field must be accepted; got "
        f"{resp.status_code} {resp.text}"
    )
    run_id = uuid.UUID(resp.json()["agent_run_id"])

    hero_imagery = pool.store.agent_runs[run_id]["metadata"].get("hero_imagery") or {}
    assert hero_imagery.get("kind") == "client_capture", (
        "AC-5: a supplied client capture must be recorded as the hero imagery (kind='client_capture')"
    )
    assert len(fake.calls) == 0, "AC-5: a client capture must not trigger any provider generation"
