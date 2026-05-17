"""s12 AC-8: provider raises ProviderError → 502 with documented body."""

from __future__ import annotations

import json
import os

import pytest

from _s12_fakes import FakeProvider
from _s12_helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_preview_provider_error_returns_502(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
        from app.providers import registry  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-8: app + providers.registry must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    failing = FakeProvider(name="openai_image", fail=True)
    monkeypatch.setattr(
        registry,
        "get_provider",
        lambda name, settings=None: failing,
        raising=False,
    )

    payload = build_payload()
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    run_id = None
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver", timeout=60.0
        ) as client:
            resp = await client.post(
                "/images/style-profile/preview",
                content=raw,
                headers={"X-Arthor-Signature": sig},
            )
        assert resp.status_code == 502, (
            f"AC-8: provider error must produce 502; got {resp.status_code} {resp.text!r}"
        )
        body = resp.json()
        assert body.get("error") == "provider_error", (
            f"AC-8: 502 body must include `error: 'provider_error'`; got {body!r}"
        )
        assert body.get("retry") is False, (
            f"AC-8: 502 body must include `retry: false`; got {body!r}"
        )
    finally:
        if run_id is not None:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
        await pool.close()
