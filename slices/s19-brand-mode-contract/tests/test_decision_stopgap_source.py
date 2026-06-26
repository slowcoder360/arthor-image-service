"""s19 AC-2/AC-5: absent brand_mode → industry stopgap derivation recorded on the run."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_absent_brand_mode_records_stopgap_source(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, _, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    # dental resolves via the industry stopgap (no explicit brand_mode) and is corpus-backed,
    # so the run completes synchronously.
    payload = build_hero_request(industry="dental", idempotency_key=f"s19-stopgap-{uuid.uuid4()}")
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

    decision = pool.store.agent_runs[run_id]["metadata"].get("hero_layout_decision")
    assert decision is not None, "AC-3: hero_layout_decision must be recorded"
    assert decision.get("brand_mode_source") == "industry_stopgap", (
        "AC-2/AC-5: deriving brand_mode from industry must record source='industry_stopgap'"
    )
