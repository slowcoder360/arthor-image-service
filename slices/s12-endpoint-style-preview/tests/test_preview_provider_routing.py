"""s12 AC-4: routing — `default_provider_hint` selects the provider; absent →
OpenAI default; unknown → 400.
"""

from __future__ import annotations

import json
import os

import pytest

from _s12_fakes import FakeProvider
from _s12_helpers import build_payload


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_preview_routes_to_named_provider(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        import asyncpg
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
        from app.providers import registry  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: app + providers.registry must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    openai_fake = FakeProvider(name="openai_image")
    gemini_fake = FakeProvider(name="google_nano_banana")

    def _fake_get_provider(name, settings=None):
        if name == "openai_image":
            return openai_fake
        if name == "google_nano_banana":
            return gemini_fake
        raise KeyError(name)

    monkeypatch.setattr(registry, "get_provider", _fake_get_provider, raising=False)

    pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2
    )
    cleanup_run_ids: list = []
    try:
        for hint, expected_provider_name in [
            ("google_nano_banana", "google_nano_banana"),
            (None, "openai_image"),
        ]:
            payload = build_payload(provider_hint=hint)
            raw = json.dumps(payload).encode()
            sig = sign_body("k", raw)
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://testserver", timeout=60.0
            ) as client:
                resp = await client.post(
                    "/images/style-profile/preview",
                    content=raw,
                    headers={"X-Arthor-Signature": sig},
                )
            assert resp.status_code == 200, (
                f"AC-4: routing case hint={hint!r} must 200; got "
                f"{resp.status_code} {resp.text!r}"
            )
            cleanup_run_ids.append(resp.json().get("agent_run_id"))
            fake = openai_fake if expected_provider_name == "openai_image" else gemini_fake
            assert fake.calls, (
                f"AC-4: hint={hint!r} must route to provider {expected_provider_name!r}"
            )

        # Unknown hint → 400
        bad_payload = build_payload(provider_hint="not_a_provider")
        bad_raw = json.dumps(bad_payload).encode()
        bad_sig = sign_body("k", bad_raw)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            bad = await client.post(
                "/images/style-profile/preview",
                content=bad_raw,
                headers={"X-Arthor-Signature": bad_sig},
            )
        assert bad.status_code == 400, (
            f"AC-4: unknown provider hint must 400; got {bad.status_code} {bad.text!r}"
        )
    finally:
        async with pool.acquire() as conn:
            for rid in cleanup_run_ids:
                if not rid:
                    continue
                await conn.execute(
                    "DELETE FROM external_media_assets WHERE agent_run_id = $1", rid
                )
                await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", rid)
                await conn.execute(
                    "DELETE FROM image_request_payloads WHERE agent_run_id = $1", rid
                )
                await conn.execute("DELETE FROM agent_runs WHERE id = $1", rid)
        await pool.close()
