"""W21-H hero-candidates endpoint tests (mocked provider + in-memory pool)."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from tests._hero_fake_pool import HeroFakePool, seed_uploaded_hero_assets


@dataclass
class _FakeCall:
    method: str
    slot_id: str | None


class _FakeProvider:
    def __init__(self, name: str = "google_nano_banana"):
        self.name = name
        self.supports_reference_image = False
        self.supports_pack_consistent = False
        self.model_version = "fake-hero-v1"
        self.calls: list[_FakeCall] = []

    async def generate_single(self, **kwargs):
        self.calls.append(
            _FakeCall(method="generate_single", slot_id=kwargs.get("slot_id"))
        )
        from app.providers.protocol import ProviderResult

        return ProviderResult(
            image_bytes=b"\x89PNGfake-hero",
            width=1920,
            height=1080,
            seed=kwargs.get("seed"),
            provider=self.name,
            model_version=self.model_version,
            cost_cents=2,
            latency_ms=3,
            external_id="fake-ext",
            response_shape={},
            determinism_level="best-effort",
        )


def _build_hero_request(*, idem_key: str | None = None) -> dict[str, Any]:
    site_id = str(uuid.uuid4())
    return {
        "site_id": site_id,
        "idempotency_key": idem_key or f"hero:{site_id}:abc123hash",
        "business": {
            "site_name": "Acme Dental",
            "industry": "dental",
            "icp_summary": "local families seeking preventive care",
            "value_prop": "gentle, modern dentistry with same-week appointments",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": [],
        },
        "location": {
            "mode": "local",
            "country": "US",
            "city": "Austin",
            "region": "TX",
            "service_areas": [],
        },
        "brand_voice": {
            "tone": "warm and reassuring",
            "notes": [],
            "style_direction": "",
            "reference_likes": [],
            "do_not": [],
        },
        "brand_visual": {
            "palette": {
                "light": {
                    "primary": "#0A4B6F",
                    "secondary": "#F4A261",
                    "background": "#FFFFFF",
                    "foreground": "#111111",
                    "muted": "#999999",
                },
                "dark": {
                    "primary": "#0A4B6F",
                    "secondary": "#F4A261",
                    "background": "#0A0A0A",
                    "foreground": "#FAFAFA",
                    "muted": "#666666",
                },
            },
            "typography": {"sans": "Inter", "heading": "Inter"},
            "register_default": "photographic",
            "logo_asset_id": None,
            "customer_reference_assets": [],
        },
        "style_profile_hint": {
            "lighting": "soft natural window light, welcoming interior",
            "camera_language": "",
            "composition_rules": [],
            "color_grading": "",
            "texture": "",
            "era_mood": None,
            "do_not": ["stock photo smiles", "clinical sterility"],
            "must_include": [],
        },
        "variants": [
            {
                "tone_angle": "search",
                "headline": "Find a dentist you trust in Austin",
                "subhead": "Same-week appointments for busy families",
            },
            {
                "tone_angle": "story",
                "headline": "Care that feels personal from the first visit",
                "subhead": "A calm office built around your comfort",
            },
            {
                "tone_angle": "offer",
                "headline": "New patient exam — book this week",
                "subhead": "Transparent pricing, no surprise fees",
            },
        ],
        "base_seed": 77,
        "default_provider_hint": "google_nano_banana",
    }


async def _prepare_app(monkeypatch, tmp_path, *, pool: HeroFakePool | None = None):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.main import app, ensure_runtime_ready

    await ensure_runtime_ready(app)
    fake = _FakeProvider()
    services = app.state.services
    services.pool = pool or HeroFakePool()
    services.providers = {"google_nano_banana": fake, "openai_image": fake}
    services.r2 = None
    services.asset_pack_semaphore = asyncio.Semaphore(4)
    return app, fake, services


@pytest.mark.asyncio
async def test_hero_post_rejects_unsigned(monkeypatch, tmp_path):
    app, _, _ = await _prepare_app(monkeypatch, tmp_path)

    from httpx import ASGITransport, AsyncClient

    payload = _build_hero_request()
    raw = json.dumps(payload).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/images/hero-candidates/generate", content=raw)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_hero_post_accepts_valid_payload_returns_202(monkeypatch, tmp_path):
    app, _, _ = await _prepare_app(monkeypatch, tmp_path)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = _build_hero_request()
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert "agent_run_id" in body


@pytest.mark.asyncio
async def test_hero_idempotency_replay_returns_same_run_id(monkeypatch, tmp_path):
    pool = HeroFakePool()
    app, _, _ = await _prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = _build_hero_request(idem_key=f"hero-idem-{uuid.uuid4()}")
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            "/images/hero-candidates/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
        second = await client.post(
            "/images/hero-candidates/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json().get("idempotent_replay") is True
    assert first.json()["agent_run_id"] == second.json()["agent_run_id"]


@pytest.mark.asyncio
async def test_hero_get_pending_then_complete_with_three_urls(monkeypatch, tmp_path):
    pool = HeroFakePool()
    app, fake, _ = await _prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = _build_hero_request(idem_key=f"hero-poll-{uuid.uuid4()}")
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)
    get_sig = sign_body("k", b"")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_resp = await client.post(
            "/images/hero-candidates/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
        assert post_resp.status_code == 202
        run_id = uuid.UUID(post_resp.json()["agent_run_id"])

        final = await client.get(
            f"/images/hero-candidates/{run_id}",
            headers={"X-Arthor-Signature": get_sig},
        )

    final_body = final.json()
    assert final_body["status"] == "complete"
    assert len(final_body["urls"]) == 3
    indices = sorted(u["variant_index"] for u in final_body["urls"])
    assert indices == [0, 1, 2]
    assert all(u.get("corpus_backed") for u in final_body["urls"])
    assert all(u.get("scene_archetype") for u in final_body["urls"])
    assert len(fake.calls) == 0


@pytest.mark.asyncio
async def test_hero_corpus_missing_returns_400(monkeypatch, tmp_path):
    app, _, _ = await _prepare_app(monkeypatch, tmp_path)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    payload = _build_hero_request(idem_key=f"hero-no-corpus-{uuid.uuid4()}")
    payload["corpus_version"] = "99.0"
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "corpus_not_available_for_industry"


@pytest.mark.asyncio
async def test_hero_live_mode_still_runs_worker(monkeypatch, tmp_path):
    pool = HeroFakePool()
    app, fake, _ = await _prepare_app(monkeypatch, tmp_path, pool=pool)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body
    import app.routes.hero_candidates as hero_routes

    worker_started = asyncio.Event()

    async def _stub_worker(services_arg, *, run_id, request, payload, style_profile):
        worker_started.set()
        await asyncio.sleep(0.05)
        seed_uploaded_hero_assets(services_arg.pool.store, run_id, count=3)
        row = services_arg.pool.store.agent_runs[run_id]
        row["status"] = "ok"
        row["finished_at"] = "now"
        fake.calls.extend(
            [_FakeCall("generate_single", f"hero_candidate_{i}") for i in range(3)]
        )

    monkeypatch.setattr(hero_routes, "run_hero_candidates_in_background", _stub_worker)

    payload = _build_hero_request(idem_key=f"hero-live-{uuid.uuid4()}")
    payload["generation_mode"] = "live"
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)
    get_sig = sign_body("k", b"")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_resp = await client.post(
            "/images/hero-candidates/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
        assert post_resp.status_code == 202
        run_id = uuid.UUID(post_resp.json()["agent_run_id"])
        await asyncio.wait_for(worker_started.wait(), timeout=2.0)
        for _ in range(40):
            poll = await client.get(
                f"/images/hero-candidates/{run_id}",
                headers={"X-Arthor-Signature": get_sig},
            )
            if poll.json().get("status") == "complete":
                break
            await asyncio.sleep(0.05)

    assert poll.json()["status"] == "complete"
    assert len(fake.calls) == 3
