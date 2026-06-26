"""s21 AC-2/AC-6/AC-7: photo-eligible corpus path preserved + now tags layout_archetype."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_corpus_path_serves_three_and_tags_archetype(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, fake, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = build_hero_request(industry="dental", idempotency_key=f"s21-photo-{uuid.uuid4()}")
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

    body = poll.json()
    assert body["status"] == "complete" and len(body["urls"]) == 3, (
        "AC-7: dental corpus behavior preserved — three corpus-backed candidates"
    )
    assert len(fake.calls) == 0, "AC-2: photo-eligible corpus path makes no provider call"
    assert all(u.get("layout_archetype") == "split_copy_image" for u in body["urls"]), (
        "AC-6: each emitted candidate must carry layout_archetype (split_copy_image for dental)"
    )
