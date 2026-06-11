"""Pod H4: hero reference assets + OpenAI edit path tests."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.payload.hero_models import HeroCandidatesRequest
from app.style.hero_reference_plan import (
    build_hero_reference_plan,
    resolve_reference_bytes_for_plan,
)
from tests._hero_fake_pool import HeroFakePool
from tests.test_hero_candidates import _build_hero_request, _prepare_app


def _with_interior_ref(raw: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(raw))
    out["brand_visual"]["customer_reference_assets"] = [
        {
            "asset_id": "ref-interior-1",
            "role": "interior",
            "url": "https://cdn.example.com/office.jpg",
            "usage_hint": "match_lighting",
            "note": "Reception area photo",
        }
    ]
    return out


def _with_team_ref(raw: dict[str, Any], *, consent: bool) -> dict[str, Any]:
    out = json.loads(json.dumps(raw))
    out["brand_visual"]["customer_reference_assets"] = [
        {
            "asset_id": "ref-team-1",
            "role": "team",
            "url": "https://cdn.example.com/doctor.jpg",
            "usage_hint": "preserve_likeness",
            "note": "Dr. Smith headshot",
            "likeness_consent": consent,
        }
    ]
    return out


def test_customer_reference_asset_accepts_usage_hint_and_note():
    raw = _with_interior_ref(_build_hero_request())
    req = HeroCandidatesRequest.model_validate(raw)
    ref = req.brand_visual.customer_reference_assets[0]
    assert ref.usage_hint == "match_lighting"
    assert ref.note == "Reception area photo"
    assert ref.likeness_consent is False


def test_build_reference_plan_interior_space_anchored():
    raw = _with_interior_ref(_build_hero_request())
    req = HeroCandidatesRequest.model_validate(raw)
    plan = build_hero_reference_plan(req)
    assert plan is not None
    assert plan["authenticity_mode"] == "space_anchored"
    assert plan["edit_enabled"] is True
    assert plan["edit_asset_id"] == "ref-interior-1"
    assert plan["edit_path"] == "openai_edit"
    assert plan["assets"][0]["usage_hint"] == "match_lighting"
    assert plan["assets"][0]["note"] == "Reception area photo"


def test_build_reference_plan_team_requires_likeness_consent():
    raw = _with_team_ref(_build_hero_request(), consent=False)
    req = HeroCandidatesRequest.model_validate(raw)
    plan = build_hero_reference_plan(req)
    assert plan is not None
    assert plan["edit_enabled"] is False
    assert plan["edit_asset_id"] is None
    assert "team_ref_ref-team-1_missing_likeness_consent" in plan["warnings"]


def test_build_reference_plan_team_with_consent_enables_edit():
    raw = _with_team_ref(_build_hero_request(), consent=True)
    req = HeroCandidatesRequest.model_validate(raw)
    plan = build_hero_reference_plan(req)
    assert plan is not None
    assert plan["authenticity_mode"] == "likeness_anchored"
    assert plan["edit_enabled"] is True
    assert plan["edit_asset_id"] == "ref-team-1"


@pytest.mark.asyncio
async def test_resolve_reference_bytes_for_plan():
    plan = {
        "edit_enabled": True,
        "edit_asset_id": "ref-interior-1",
        "assets": [
            {
                "asset_id": "ref-interior-1",
                "url": "https://cdn.example.com/office.jpg",
            }
        ],
        "warnings": [],
    }

    async def fake_fetch(url: str) -> bytes:
        assert url == "https://cdn.example.com/office.jpg"
        return b"\x89PNGref-bytes"

    resolved, updated = await resolve_reference_bytes_for_plan(plan, fetch_url=fake_fetch)
    assert resolved == [b"\x89PNGref-bytes"]
    assert updated is not None
    assert updated["assets"][0]["resolved"] is True
    assert updated["assets"][0]["byte_len"] == len(b"\x89PNGref-bytes")


@dataclass
class _TrackingFakeProvider:
    name: str = "openai_image"
    supports_reference_image: bool = True
    supports_pack_consistent: bool = False
    model_version: str = "fake-openai-v1"
    reference_calls: list[list[bytes] | None] = field(default_factory=list)

    async def generate_single(self, **kwargs):
        refs = kwargs.get("reference_images")
        self.reference_calls.append(refs)
        from app.providers.protocol import ProviderResult

        method = "edit" if refs else "generate"
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
            response_shape={"method": method},
            determinism_level="best-effort",
        )


@pytest.mark.asyncio
async def test_generate_one_variant_passes_reference_to_openai_edit(monkeypatch, tmp_path):
    pool = HeroFakePool()
    _, _, services = await _prepare_app(monkeypatch, tmp_path, pool=pool)
    fake = _TrackingFakeProvider()
    services.providers = {"openai_image": fake}
    services.settings.hero_prompt_cache_enabled = False

    raw = _with_interior_ref(_build_hero_request())
    req = HeroCandidatesRequest.model_validate(raw)
    from app.payload.hero_models import hero_request_to_payload_v1, variant_to_slot
    from app.orchestration.hero_worker import _VariantJob, _generate_one_variant
    from app.style.resolver import resolve_style_profile

    payload = hero_request_to_payload_v1(req)
    style_profile = await resolve_style_profile(payload)
    run_id = uuid.uuid4()
    slot = variant_to_slot(req, req.variants[0], 0)
    asset_id = uuid.uuid4()
    job = _VariantJob(
        index=0,
        provider_prompt="compiled hero prompt",
        prompt_hash="abc123",
        entry=None,
        asset_id=asset_id,
        slot=slot,
        seed=77,
    )

    async def _fake_finalize(*args, **kwargs):
        return "https://example.com/hero.png"

    monkeypatch.setattr(
        "app.orchestration.hero_worker._finalize_hero_slot",
        _fake_finalize,
    )
    monkeypatch.setattr(
        "app.orchestration.hero_worker._hero_post_check_modes",
        lambda *args, **kwargs: [],
    )

    ok, cache_hit = await _generate_one_variant(
        pool,
        services,
        run_id=run_id,
        request=req,
        style_profile=style_profile,
        provider=fake,
        pname="openai_image",
        palette_hex=["#000000"],
        job=job,
        reference_images=[b"\x89PNGcustomer-ref"],
    )

    assert ok is True
    assert cache_hit is False
    assert len(fake.reference_calls) == 1
    assert fake.reference_calls[0] == [b"\x89PNGcustomer-ref"]
    assert fake.reference_calls[0] is not None


@pytest.mark.asyncio
async def test_hero_post_persists_reference_plan_in_metadata(monkeypatch, tmp_path):
    pool = HeroFakePool()
    app, _, _ = await _prepare_app(monkeypatch, tmp_path, pool=pool)

    import app.routes.hero_candidates as hero_routes

    async def _noop_worker(*args, **kwargs):
        return None

    monkeypatch.setattr(hero_routes, "run_hero_candidates_in_background", _noop_worker)

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body

    raw = _with_interior_ref(_build_hero_request(idem_key=f"hero-meta-{uuid.uuid4()}"))
    body_bytes = json.dumps(raw).encode()
    sig = sign_body("k", body_bytes)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/generate",
            content=body_bytes,
            headers={"X-Arthor-Signature": sig},
        )

    assert resp.status_code == 202
    run_id = uuid.UUID(resp.json()["agent_run_id"])
    run_md = pool.store.agent_runs[run_id]["metadata"]
    assert "reference_plan" in run_md
    assert run_md["reference_plan"]["edit_asset_id"] == "ref-interior-1"


@pytest.mark.asyncio
async def test_openai_provider_edit_path_with_mocked_client():
    import base64

    from app.providers.openai_image import OpenAIImageProvider

    class _Datum:
        b64_json = base64.b64encode(b"\x89PNG\r\n\x1a\nfake-bytes-here").decode()

    class _Resp:
        model = "gpt-image-2"
        created = 1700000000
        data = [_Datum()]
        id = "img-edit-1"

    class _FakeImages:
        def __init__(self):
            self.edit_calls: list[dict] = []
            self.generate_calls: list[dict] = []

        async def edit(self, **kwargs):
            self.edit_calls.append(kwargs)
            return _Resp()

        async def generate(self, **kwargs):
            self.generate_calls.append(kwargs)
            return _Resp()

    class _FakeClient:
        def __init__(self):
            self.images = _FakeImages()

    client = _FakeClient()
    provider = OpenAIImageProvider(client, model_version="gpt-image-2")

    ref_bytes = b"\x89PNGreference-image"
    result = await provider.generate_single(
        prompt="warm dental hero with matched lighting",
        dimensions=(1920, 1080),
        seed=None,
        style_profile=None,
        reference_images=[ref_bytes],
    )

    assert len(client.images.edit_calls) == 1
    assert client.images.generate_calls == []
    assert result.image_bytes == b"\x89PNG\r\n\x1a\nfake-bytes-here"
    edit_call = client.images.edit_calls[0]
    assert edit_call["prompt"] == "warm dental hero with matched lighting"
    assert edit_call["size"] == "1920x1080"
