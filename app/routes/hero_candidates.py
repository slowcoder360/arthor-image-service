"""W21-H hero-candidates HTTP entrypoints (narrow builder contract)."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.auth.hmac import require_hmac, require_hmac_get
from app.orchestration.hero_worker import (
    plan_hero_variant_regenerate,
    run_hero_candidates_in_background,
    run_hero_variant_regenerate_in_background,
)
from app.orchestration.pack_worker import get_image_provider_for_services
from app.payload.hero_models import (
    HeroCandidatesRequest,
    HeroRegenerateVariantBody,
    build_hero_copy_overlay_metadata,
    hero_request_to_payload_v1,
    variant_to_slot,
)
from app.payload.models import PayloadV1
from app.payload.idempotency import lookup_idempotency_key
from app.payload.repository import IdempotencyConflict, insert_raw_payload_record
from app.runs.agent_runs import insert_pending_run, update_run_status
from app.storage.uploader import browser_url_for
from app.storage.asset_writer import insert_pending_asset
from app.style.prompt_improver import finalize_hero_triad_prompts
from app.style.resolver import resolve_style_profile, style_profile_to_metadata
from app.style.hero_visual_strategy import resolve_hero_visual_strategy
from app.style.hero_reference_plan import build_hero_reference_plan
from app.style.hero_taste_corpus import fulfill_corpus_hero_run, resolve_taste_corpus
from app.style.profile import StyleProfile
from app.style.hero_abstract_prompt import build_abstract_hero_prompt
from app.layout.resolver import HeroLayoutDecision, resolve_hero_layout_archetype

router = APIRouter()

HeroPollStatus = Literal["pending", "running", "complete", "partial", "failed"]


def _map_poll_status(
    db_status: str,
    *,
    uploaded: int,
    failed: int,
    expected: int = 3,
) -> HeroPollStatus:
    if db_status == "failed":
        return "failed"
    if db_status == "running":
        if uploaded == 0 and failed == 0:
            return "pending"
        return "running"
    if db_status == "ok":
        if uploaded >= expected:
            return "complete"
        if uploaded > 0:
            return "partial"
        return "failed"
    return "running"


def _hero_palette_primary(hero_req: HeroCandidatesRequest) -> str:
    try:
        return str(hero_req.brand_visual.palette.light.primary)
    except AttributeError:
        return "#222222"


def _abstract_hero_imagery(
    decision: HeroLayoutDecision,
    hero_req: HeroCandidatesRequest,
    *,
    fallback_from: str | None = None,
) -> dict[str, Any]:
    signal: dict[str, Any] = {
        "kind": "abstract",
        "imagery_type": "generative_abstract",
        "prompt": build_abstract_hero_prompt(
            palette_primary=_hero_palette_primary(hero_req),
            seed=hero_req.base_seed,
            variant_index=0,
        ),
    }
    if fallback_from:
        signal["fallback_from"] = fallback_from
    return signal


def _resolve_nonphoto_hero_imagery(
    decision: HeroLayoutDecision,
    hero_req: HeroCandidatesRequest,
) -> dict[str, Any]:
    """Typed hero imagery signal for non-photo archetypes — never a synthetic screenshot."""
    if decision.imagery_type == "none" or decision.archetype == "typographic_no_image":
        return {"kind": "none", "reason": decision.archetype}
    if decision.archetype == "product_screenshot":
        capture = hero_req.product_capture_url
        if capture:
            return {"kind": "client_capture", "url": str(capture), "imagery_type": "product_ui"}
        # No client capture: fall back deterministically — never synthesize a screenshot.
        return _abstract_hero_imagery(decision, hero_req, fallback_from="product_screenshot")
    return _abstract_hero_imagery(decision, hero_req)


def _parse_hero_request(raw: bytes) -> HeroCandidatesRequest:
    try:
        return HeroCandidatesRequest.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc


@router.post("/images/hero-candidates/generate")
async def generate_hero_candidates(request: Request) -> JSONResponse:
    raw = await require_hmac(request)
    services = request.app.state.services
    hero_req = _parse_hero_request(raw)

    pool = getattr(services, "pool", None)
    if pool is None:
        return JSONResponse(status_code=503, content={"detail": "database_unavailable"})

    layout_decision = resolve_hero_layout_archetype(
        brand_mode=hero_req.brand_mode,
        industry=hero_req.business.industry,
    )

    # Non-photo archetypes never touch the photographic taste corpus.
    use_corpus = hero_req.generation_mode == "corpus" and layout_decision.scene_catalog_eligible
    corpus = None
    if use_corpus:
        corpus = resolve_taste_corpus(hero_req.business.industry, corpus_version=hero_req.corpus_version)
        if corpus is None:
            if hero_req.corpus_fallback == "live":
                use_corpus = False
            else:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "corpus_not_available_for_industry"},
                )

    maybe_existing = await lookup_idempotency_key(pool, hero_req.idempotency_key)
    if maybe_existing is not None:
        poll = await _build_poll_response(pool, maybe_existing, services.settings)
        return JSONResponse(
            status_code=200,
            content={
                "agent_run_id": str(maybe_existing),
                "status": poll["status"],
                "idempotent_replay": True,
            },
        )

    payload = hero_request_to_payload_v1(hero_req)
    completeness = payload.payload_completeness_score()

    run_id = await insert_pending_run(
        pool,
        run_type="hero_candidates_generation",
        site_id=hero_req.site_id,
        metadata={
            "payload_completeness_score": completeness,
            "hero_candidates": True,
        },
    )

    try:
        await insert_raw_payload_record(
            pool,
            agent_run_id=run_id,
            payload=hero_req.model_dump(mode="json"),
            payload_version=hero_req.payload_version,
            idempotency_key=hero_req.idempotency_key,
        )
    except IdempotencyConflict:
        other_id = await lookup_idempotency_key(pool, hero_req.idempotency_key)
        if other_id is not None:
            poll = await _build_poll_response(pool, other_id, services.settings)
            return JSONResponse(
                status_code=200,
                content={
                    "agent_run_id": str(other_id),
                    "status": poll["status"],
                    "idempotent_replay": True,
                },
            )
        raise

    style_profile = await resolve_style_profile(payload)
    visual_strategy = resolve_hero_visual_strategy(hero_req)
    reference_plan = build_hero_reference_plan(hero_req)
    compiled_prompts: list[Any] = []
    improver_stats = None
    if not use_corpus and layout_decision.scene_catalog_eligible:
        compiled_prompts = await finalize_hero_triad_prompts(
            services,
            hero_req,
            style_profile,
            desktop_seed_edit=hero_req.source_desktop_run_id is not None,
        )
        improver_stats = getattr(services, "_last_hero_improver_stats", None)
    effective_mode = "corpus" if use_corpus else "live"
    metadata_patch: dict[str, Any] = {
        "style_profile": style_profile_to_metadata(style_profile),
        "hero_visual_strategy": visual_strategy.to_dict(),
        "generation_mode": effective_mode,
        "corpus_version": hero_req.corpus_version if use_corpus else None,
        "hero_viewport": hero_req.hero_viewport,
        "hero_copy_overlay": build_hero_copy_overlay_metadata(hero_req),
        "payload_version": hero_req.payload_version,
        "hero_layout_decision": layout_decision.to_dict(),
    }
    if use_corpus:
        metadata_patch["corpus_industry_label"] = corpus.industry_label if corpus else None
        if corpus is not None and corpus.slug:
            metadata_patch["corpus_slug"] = corpus.slug
    elif layout_decision.scene_catalog_eligible:
        metadata_patch["hero_provider_prompts"] = [p.to_dict() for p in compiled_prompts]
        metadata_patch["hero_prompt_compiler_version"] = (
            compiled_prompts[0].compiler_version if compiled_prompts else None
        )
    else:
        metadata_patch["hero_imagery"] = _resolve_nonphoto_hero_imagery(layout_decision, hero_req)
    if hero_req.source_desktop_run_id is not None:
        metadata_patch["source_desktop_run_id"] = str(hero_req.source_desktop_run_id)
        metadata_patch["desktop_seed_edit"] = True
    if reference_plan is not None:
        metadata_patch["reference_plan"] = reference_plan
    if improver_stats:
        metadata_patch["hero_prompt_improver_stats"] = improver_stats
    await update_run_status(
        pool,
        run_id,
        status="running",
        metadata_patch=metadata_patch,
    )

    if not layout_decision.scene_catalog_eligible:
        # Non-photo hero: emit the decision + imagery signal; no photographic generation.
        await update_run_status(pool, run_id, status="ok", finished=True)
    elif use_corpus and corpus is not None:
        await fulfill_corpus_hero_run(
            pool,
            run_id=run_id,
            request=hero_req,
            style_profile=style_profile,
            corpus=corpus,
            settings=services.settings,
        )
        await update_run_status(pool, run_id, status="ok", finished=True)
    else:
        asyncio.create_task(
            run_hero_candidates_in_background(
                services,
                run_id=run_id,
                request=hero_req,
                payload=payload,
                style_profile=style_profile,
            )
        )

    return JSONResponse(
        status_code=202,
        content={"agent_run_id": str(run_id), "status": "accepted"},
    )


async def _build_poll_response(
    pool: Any,
    run_id: uuid.UUID,
    settings: Any,
    *,
    picked_variant_index: int | None = None,
) -> dict[str, Any]:
    async with pool.acquire() as conn:
        run_row = await conn.fetchrow(
            "SELECT status, finished_at, metadata FROM agent_runs WHERE id = $1",
            run_id,
        )
        if run_row is None:
            raise HTTPException(status_code=404, detail="run_not_found")

        assets = await conn.fetch(
            """
            SELECT r2_url, r2_key, status, metadata
            FROM external_media_assets
            WHERE agent_run_id = $1
            ORDER BY created_at ASC
            """,
            run_id,
        )

    uploaded = sum(1 for a in assets if str(a["status"]) == "uploaded")
    failed = sum(1 for a in assets if str(a["status"]) == "failed")
    poll_status = _map_poll_status(str(run_row["status"]), uploaded=uploaded, failed=failed)

    run_md_early = run_row["metadata"]
    if isinstance(run_md_early, str):
        run_md_early = json.loads(run_md_early)
    layout_decision_md = run_md_early.get("hero_layout_decision") if isinstance(run_md_early, dict) else None

    urls: list[dict[str, Any]] = []
    for row in assets:
        if str(row["status"]) != "uploaded" or not row["r2_url"]:
            continue
        md = row["metadata"]
        if isinstance(md, str):
            md = json.loads(md)
        if not isinstance(md, dict):
            md = {}
        r2_key_val = row.get("r2_key")
        entry: dict[str, Any] = {
            "variant_index": md.get("variant_index"),
            "url": browser_url_for(
                settings,
                r2_key=str(r2_key_val) if r2_key_val else None,
                stored_url=str(row["r2_url"]) if row["r2_url"] else None,
            ),
        }
        if md.get("tone_angle") is not None:
            entry["tone_angle"] = md["tone_angle"]
        if md.get("headline") is not None:
            entry["headline"] = md["headline"]
        if md.get("subhead") is not None:
            entry["subhead"] = md["subhead"]
        if md.get("failure_mode") is not None:
            entry["failure_mode"] = md["failure_mode"]
        if md.get("scene_archetype") is not None:
            entry["scene_archetype"] = md["scene_archetype"]
        if md.get("style_profile_fragment") is not None:
            entry["style_profile_fragment"] = md["style_profile_fragment"]
        if md.get("corpus_backed"):
            entry["corpus_backed"] = True
        if isinstance(layout_decision_md, dict):
            if layout_decision_md.get("archetype"):
                entry["layout_archetype"] = layout_decision_md["archetype"]
            if layout_decision_md.get("imagery_type"):
                entry["imagery_type"] = layout_decision_md["imagery_type"]
        urls.append(entry)

    urls.sort(key=lambda u: (u.get("variant_index") is None, u.get("variant_index", 0)))

    run_md = run_row["metadata"]
    if isinstance(run_md, str):
        run_md = json.loads(run_md)
    if not isinstance(run_md, dict):
        run_md = {}
    error = run_md.get("error") if poll_status == "failed" else None

    out: dict[str, Any] = {
        "agent_run_id": str(run_id),
        "status": poll_status,
        "urls": urls,
    }
    if error:
        out["error"] = error
    if picked_variant_index is not None:
        picked = next(
            (u for u in urls if u.get("variant_index") == picked_variant_index),
            None,
        )
        if picked is not None:
            out["picked_variant"] = picked
    return out


def _metadata_as_dict(meta: Any) -> dict[str, Any]:
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str):
        return json.loads(meta)
    return dict(meta)


async def _style_profile_from_hero_run(
    pool: Any,
    *,
    original_run_id: uuid.UUID,
    payload: PayloadV1,
) -> StyleProfile:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT metadata FROM agent_runs WHERE id = $1",
            original_run_id,
        )
    meta = _metadata_as_dict(row["metadata"]) if row else {}
    raw_sp = meta.get("style_profile")
    if isinstance(raw_sp, dict) and raw_sp.get("palette"):
        try:
            return StyleProfile.model_validate(raw_sp)
        except ValidationError:
            pass
    return await resolve_style_profile(payload)


def _original_hero_asset_seed(asset_meta: dict[str, Any], request: HeroCandidatesRequest, index: int) -> int:
    raw = asset_meta.get("seed")
    if raw is not None:
        return int(raw)
    return int(request.base_seed + index)


@router.post("/images/hero-candidates/regenerate-variant")
async def regenerate_hero_variant(request: Request) -> JSONResponse:
    """Regenerate one hero triad variant with a typed edit_kind (mirrors pack regenerate-slot)."""
    raw = await require_hmac(request)
    services = request.app.state.services
    pool = getattr(services, "pool", None)
    if pool is None:
        return JSONResponse(status_code=503, content={"detail": "database_unavailable"})

    try:
        body = HeroRegenerateVariantBody.model_validate(json.loads(raw.decode()))
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    async with pool.acquire() as conn:
        asset_row = await conn.fetchrow(
            """
            SELECT id, status, agent_run_id, site_id, metadata
            FROM external_media_assets
            WHERE id = $1
            """,
            body.asset_id,
        )
        if asset_row is None:
            return JSONResponse(status_code=404, content={"detail": "unknown_asset_id"})

        if str(asset_row["status"]) != "uploaded":
            return JSONResponse(status_code=400, content={"detail": "asset_must_be_uploaded"})

        asset_meta = _metadata_as_dict(asset_row["metadata"])
        if not asset_meta.get("hero_candidate"):
            return JSONResponse(status_code=400, content={"detail": "asset_not_hero_candidate"})
        if asset_meta.get("variant_index") is None:
            return JSONResponse(status_code=400, content={"detail": "asset_missing_variant_index"})

        variant_index = int(asset_meta["variant_index"])

        payload_row = await conn.fetchrow(
            """
            SELECT payload
            FROM image_request_payloads
            WHERE agent_run_id = $1
            """,
            asset_row["agent_run_id"],
        )
        if payload_row is None:
            return JSONResponse(status_code=400, content={"detail": "original_payload_missing"})

    try:
        raw_payload = payload_row["payload"]
        if isinstance(raw_payload, str):
            raw_payload = json.loads(raw_payload)
        hero_req = HeroCandidatesRequest.model_validate(raw_payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    payload = hero_request_to_payload_v1(hero_req)
    style_profile = await _style_profile_from_hero_run(
        pool,
        original_run_id=asset_row["agent_run_id"],
        payload=payload,
    )
    original_seed = _original_hero_asset_seed(asset_meta, hero_req, variant_index)

    try:
        compiled, req_eff, edit_meta = plan_hero_variant_regenerate(
            hero_req,
            variant_index=variant_index,
            edit_kind=body.edit_kind,
            style_profile=style_profile,
            original_seed=original_seed,
            new_seed=body.new_seed,
            prompt_modifier=body.prompt_modifier,
            scene_archetype=body.scene_archetype,
            customer_reference_assets=body.customer_reference_assets,
            source_hero_asset_id=body.source_hero_asset_id,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    pname = "openai_image"
    provider = get_image_provider_for_services(services, pname)
    model_version = getattr(provider, "model_version", "unknown")
    slot = req_eff.variants[variant_index]
    slot_obj = variant_to_slot(req_eff, slot, variant_index)
    pending_meta: dict[str, Any] = {
        "slot_id": slot_obj.slot_id,
        "variant_index": variant_index,
        "slot_intent": slot_obj.intent,
        "style_profile_id": str(style_profile.id),
        "prompt_hash": compiled.prompt_hash,
        "seed": edit_meta["seed"],
        "determinism_level": "best-effort",
        "run_id": "",
        "hero_candidate": True,
        "edit_kind": body.edit_kind,
    }

    new_run_id = await insert_pending_run(
        pool,
        run_type="hero_variant_regenerate",
        site_id=hero_req.site_id,
        parent_run_id=asset_row["agent_run_id"],
        metadata={
            "original_asset_id": str(body.asset_id),
            "edit_kind": body.edit_kind,
            "variant_index": variant_index,
            "style_profile": style_profile_to_metadata(style_profile),
            "hero_provider_prompts": [compiled.to_dict()],
            "hero_prompt_compiler_version": compiled.compiler_version,
            **({"reference_plan": edit_meta["reference_plan"]} if edit_meta.get("reference_plan") else {}),
            **(
                {"source_hero_asset_id": edit_meta["source_hero_asset_id"]}
                if edit_meta.get("source_hero_asset_id")
                else {}
            ),
        },
    )
    pending_meta["run_id"] = str(new_run_id)

    new_asset_id = await insert_pending_asset(
        pool,
        agent_run_id=new_run_id,
        site_id=hero_req.site_id,
        provider=pname,
        model_version=model_version,
        metadata=pending_meta,
    )

    asyncio.create_task(
        run_hero_variant_regenerate_in_background(
            services,
            new_run_id=new_run_id,
            old_asset_id=body.asset_id,
            request=req_eff,
            style_profile=style_profile,
            variant_index=variant_index,
            provider_prompt=compiled.prompt,
            prompt_hash=compiled.prompt_hash,
            seed=int(edit_meta["seed"]),
            pending_asset_id=new_asset_id,
            edit_kind=body.edit_kind,
            source_hero_asset_id=body.source_hero_asset_id,
        )
    )

    return JSONResponse(
        status_code=202,
        content={
            "agent_run_id": str(new_run_id),
            "new_asset_id": str(new_asset_id),
            "status": "accepted",
        },
    )


@router.get("/images/hero-candidates/{run_id}")
async def get_hero_candidates_status(
    run_id: uuid.UUID,
    request: Request,
    picked_variant_index: int | None = None,
) -> JSONResponse:
    await require_hmac_get(request)
    services = request.app.state.services
    pool = getattr(services, "pool", None)
    if pool is None:
        return JSONResponse(status_code=503, content={"detail": "database_unavailable"})

    body = await _build_poll_response(
        pool,
        run_id,
        services.settings,
        picked_variant_index=picked_variant_index,
    )
    return JSONResponse(status_code=200, content=body)
