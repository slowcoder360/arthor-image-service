"""Pod H5 — hero regenerate-variant endpoint + supersession tests."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import pytest

from tests._hero_fake_pool import HeroFakePool, seed_uploaded_hero_assets
from tests.test_hero_candidates import _FakeProvider, _build_hero_request, _prepare_app


def _seed_hero_run_with_asset(
    store: Any,
    *,
    hero_payload: dict[str, Any],
    variant_index: int = 0,
    seed: int = 77,
) -> tuple[uuid.UUID, uuid.UUID]:
    run_id = uuid.uuid4()
    store.agent_runs[run_id] = {
        "id": run_id,
        "run_type": "hero_candidates_generation",
        "status": "ok",
        "metadata": {},
        "finished_at": "now",
    }
    store.payloads.append(
        {
            "agent_run_id": run_id,
            "payload": hero_payload,
        }
    )
    asset_id = uuid.uuid4()
    store.assets.append(
        {
            "id": asset_id,
            "agent_run_id": run_id,
            "site_id": uuid.UUID(hero_payload["site_id"]),
            "status": "uploaded",
            "r2_key": f"hero-candidates/{run_id}/{variant_index}.png",
            "r2_url": f"https://r2.example/hero-candidates/{run_id}/{variant_index}.png",
            "metadata": {
                "variant_index": variant_index,
                "hero_candidate": True,
                "slot_id": f"hero_candidate_{variant_index}",
                "slot_intent": "homepage hero",
                "style_profile_id": str(uuid.uuid4()),
                "prompt_hash": "abc",
                "seed": seed,
                "determinism_level": "best-effort",
                "run_id": str(run_id),
            },
            "created_ord": variant_index,
        }
    )
    return run_id, asset_id


@pytest.mark.asyncio
async def test_hero_regenerate_rejects_unsigned(monkeypatch, tmp_path):
    app, _, _ = await _prepare_app(monkeypatch, tmp_path)
    from httpx import ASGITransport, AsyncClient

    body = {"asset_id": str(uuid.uuid4()), "edit_kind": "retry"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/regenerate-variant",
            content=json.dumps(body).encode(),
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_hero_regenerate_unknown_asset_404(monkeypatch, tmp_path):
    app, _, _ = await _prepare_app(monkeypatch, tmp_path)
    from httpx import ASGITransport, AsyncClient
    from app.auth.hmac import sign_body

    body = {"asset_id": str(uuid.uuid4()), "edit_kind": "retry"}
    raw = json.dumps(body).encode()
    sig = sign_body("k", raw)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/regenerate-variant",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hero_regenerate_tweak_requires_modifier(monkeypatch, tmp_path):
    pool = HeroFakePool()
    app, _, _ = await _prepare_app(monkeypatch, tmp_path, pool=pool)
    from httpx import ASGITransport, AsyncClient
    from app.auth.hmac import sign_body

    payload = _build_hero_request()
    _, asset_id = _seed_hero_run_with_asset(pool.store, hero_payload=payload)

    body = {"asset_id": str(asset_id), "edit_kind": "tweak"}
    raw = json.dumps(body).encode()
    sig = sign_body("k", raw)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/regenerate-variant",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
    assert resp.status_code == 400
    assert "tweak_requires_prompt_modifier" in resp.text


@pytest.mark.asyncio
async def test_hero_regenerate_retry_accepts_returns_202(monkeypatch, tmp_path):
    pool = HeroFakePool()
    app, _, _ = await _prepare_app(monkeypatch, tmp_path, pool=pool)
    import app.routes.hero_candidates as hero_routes
    from httpx import ASGITransport, AsyncClient
    from app.auth.hmac import sign_body

    worker_started = asyncio.Event()

    async def _stub_regen(services, **kwargs):
        worker_started.set()

    monkeypatch.setattr(hero_routes, "run_hero_variant_regenerate_in_background", _stub_regen)

    payload = _build_hero_request()
    _, asset_id = _seed_hero_run_with_asset(pool.store, hero_payload=payload, seed=77)

    body = {"asset_id": str(asset_id), "edit_kind": "retry"}
    raw = json.dumps(body).encode()
    sig = sign_body("k", raw)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/images/hero-candidates/regenerate-variant",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "accepted"
    assert "agent_run_id" in data
    assert "new_asset_id" in data
    await asyncio.wait_for(worker_started.wait(), timeout=2.0)


@pytest.mark.asyncio
async def test_hero_regenerate_supersedes_old_asset(monkeypatch, tmp_path):
    pool = HeroFakePool()
    app, fake, services = await _prepare_app(monkeypatch, tmp_path, pool=pool)
    from app.orchestration.hero_worker import run_hero_variant_regenerate_in_background
    from app.orchestration.hero_worker import plan_hero_variant_regenerate
    from app.payload.hero_models import HeroCandidatesRequest, hero_request_to_payload_v1
    from app.runs.agent_runs import insert_pending_run
    from app.storage.asset_writer import insert_pending_asset
    from app.style.resolver import resolve_style_profile

    payload = _build_hero_request()
    hero_req = HeroCandidatesRequest.model_validate(payload)
    style_profile = await resolve_style_profile(hero_request_to_payload_v1(hero_req))
    run_id, old_asset_id = _seed_hero_run_with_asset(pool.store, hero_payload=payload, seed=77)

    compiled, req_eff, edit_meta = plan_hero_variant_regenerate(
        hero_req,
        variant_index=0,
        edit_kind="retry",
        style_profile=style_profile,
        original_seed=77,
    )
    variant = req_eff.variants[0]
    from app.payload.hero_models import variant_to_slot

    slot_obj = variant_to_slot(req_eff, variant, 0)
    new_run_id = await insert_pending_run(
        pool,
        run_type="hero_variant_regenerate",
        site_id=hero_req.site_id,
        parent_run_id=run_id,
        metadata={"original_asset_id": str(old_asset_id), "edit_kind": "retry"},
    )
    pending_meta = {
        "slot_id": slot_obj.slot_id,
        "variant_index": 0,
        "slot_intent": slot_obj.intent,
        "style_profile_id": str(style_profile.id),
        "prompt_hash": compiled.prompt_hash,
        "seed": edit_meta["seed"],
        "determinism_level": "best-effort",
        "run_id": str(new_run_id),
        "hero_candidate": True,
    }
    new_asset_id = await insert_pending_asset(
        pool,
        agent_run_id=new_run_id,
        site_id=hero_req.site_id,
        provider="openai_image",
        model_version=fake.model_version,
        metadata=pending_meta,
    )

    monkeypatch.setattr(
        "app.orchestration.hero_worker.run_hero_post_checks",
        lambda *a, **k: frozenset(),
    )
    monkeypatch.setattr(
        "app.quality.palette_variance.check_palette_drift",
        lambda *a, **k: (False, []),
    )

    await run_hero_variant_regenerate_in_background(
        services,
        new_run_id=new_run_id,
        old_asset_id=old_asset_id,
        request=req_eff,
        style_profile=style_profile,
        variant_index=0,
        provider_prompt=compiled.prompt,
        prompt_hash=compiled.prompt_hash,
        seed=int(edit_meta["seed"]),
        pending_asset_id=new_asset_id,
        edit_kind="retry",
    )

    old_asset = next(a for a in pool.store.assets if a["id"] == old_asset_id)
    new_asset = next(a for a in pool.store.assets if a["id"] == new_asset_id)
    assert old_asset["status"] == "superseded"
    assert old_asset["metadata"].get("replaced_by") == str(new_asset_id)
    assert new_asset["status"] == "uploaded"
    assert edit_meta["seed"] == 78


@pytest.mark.asyncio
async def test_hero_regenerate_rescene_changes_prompt_archetype(monkeypatch, tmp_path):
    from app.payload.hero_models import HeroCandidatesRequest, hero_request_to_payload_v1
    from app.orchestration.hero_worker import plan_hero_variant_regenerate
    from app.style.resolver import resolve_style_profile

    payload = _build_hero_request()
    hero_req = HeroCandidatesRequest.model_validate(payload)
    style_profile = await resolve_style_profile(hero_request_to_payload_v1(hero_req))

    compiled, _, edit_meta = plan_hero_variant_regenerate(
        hero_req,
        variant_index=0,
        edit_kind="rescene",
        style_profile=style_profile,
        original_seed=77,
        scene_archetype="threshold_invitation",
    )
    assert edit_meta["scene_archetype"] == "threshold_invitation"
    assert compiled.scene_archetype == "threshold_invitation"
    assert "threshold_invitation" in compiled.prompt
