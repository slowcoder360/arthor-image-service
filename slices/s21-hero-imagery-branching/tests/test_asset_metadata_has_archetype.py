"""s21 AC-6: every emitted candidate records layout_archetype + imagery_type; poll surfaces it."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_poll_surfaces_archetype_and_imagery_type(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, _, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = build_hero_request(industry="dental", idempotency_key=f"s21-meta-{uuid.uuid4()}")
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)
    get_sig = sign_body("k", b"")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post = await client.post(
            "/images/hero-candidates/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )
        run_id = uuid.UUID(post.json()["agent_run_id"])
        poll = await client.get(
            f"/images/hero-candidates/{run_id}", headers={"X-Arthor-Signature": get_sig}
        )

    urls = poll.json().get("urls", [])
    assert urls, "expected corpus candidates"
    for u in urls:
        assert u.get("layout_archetype"), "AC-6: poll entries must surface layout_archetype"
        assert u.get("imagery_type"), "AC-6: poll entries must surface imagery_type"
