"""s10 AC-3: same idempotency_key second time → 200 + idempotent_replay: true."""

from __future__ import annotations

import json
import os

import pytest

from _helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_idempotent_replay_returns_200_with_flag(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app + sign_body must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    payload = build_payload()
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            "/images/asset-pack/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )
        assert first.status_code == 202, (
            f"AC-3: first call must 202; got {first.status_code} {first.text!r}"
        )

        second = await client.post(
            "/images/asset-pack/generate", content=raw, headers={"X-Arthor-Signature": sig}
        )
    assert second.status_code == 200, (
        f"AC-3: replay must 200; got {second.status_code} {second.text!r}"
    )
    body = second.json()
    assert body.get("idempotent_replay") is True, (
        "AC-3: replay body must include `idempotent_replay: true`"
    )
    assert "agent_run_id" in body, (
        "AC-3: replay body must echo the original agent_run_id"
    )
