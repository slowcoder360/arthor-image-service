"""s21 AC-4: typographic_no_image emits a typed no-image signal and makes zero provider calls."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_typographic_emits_no_image_signal(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, fake, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    import app.routes.hero_candidates as hero_routes
    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    async def _noop_worker(*args, **kwargs):
        return None

    monkeypatch.setattr(hero_routes, "run_hero_candidates_in_background", _noop_worker)

    payload = build_hero_request(
        industry="design studio",
        brand_mode="creative_portfolio",
        generation_mode="live",
        idempotency_key=f"s21-typo-{uuid.uuid4()}",
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
    hero_imagery = meta.get("hero_imagery")
    assert hero_imagery and hero_imagery.get("kind") == "none", (
        "AC-4: typographic_no_image must emit hero_imagery.kind == 'none'"
    )
    assert len(fake.calls) == 0, "AC-4: typographic_no_image must make zero provider calls"
