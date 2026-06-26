"""s19 AC-3/AC-5: an explicit brand_mode is recorded on the run as hero_layout_decision."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_explicit_brand_mode_recorded_on_run(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, _, services = await prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = build_hero_request(brand_mode="agency", idempotency_key=f"s19-explicit-{uuid.uuid4()}")
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
    assert resp.status_code in (202, 200), f"unexpected status {resp.status_code}: {resp.text}"
    run_id = uuid.UUID(resp.json()["agent_run_id"])

    meta = pool.store.agent_runs[run_id]["metadata"]
    decision = meta.get("hero_layout_decision")
    assert decision is not None, (
        "AC-3: generate must record hero_layout_decision on the run metadata"
    )
    assert decision.get("brand_mode_source") == "explicit", (
        "AC-5: an explicit brand_mode must record brand_mode_source='explicit'"
    )
