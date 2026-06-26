"""s21 AC-1 boundary: image-service emits imagery / typed signals — never HTML markup."""

from __future__ import annotations

import json
import uuid

import pytest

from _layout_helpers import build_hero_request, prepare_app


@pytest.mark.asyncio
async def test_response_carries_no_html(monkeypatch, tmp_path):
    from tests._hero_fake_pool import HeroFakePool

    pool = HeroFakePool()
    app, _, _ = await prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = build_hero_request(industry="dental", idempotency_key=f"s21-nohtml-{uuid.uuid4()}")
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

    text = poll.text.lower()
    for marker in ("<div", "<section", "<html", "<header", "class=\""):
        assert marker not in text, (
            f"AC boundary: image-service must emit decision + imagery, never HTML (found {marker!r})"
        )
