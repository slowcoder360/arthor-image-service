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
from app.orchestration.hero_worker import run_hero_candidates_in_background
from app.payload.hero_models import (
    HeroCandidatesRequest,
    build_hero_copy_overlay_metadata,
    hero_request_to_payload_v1,
)
from app.payload.idempotency import lookup_idempotency_key
from app.payload.repository import IdempotencyConflict, insert_raw_payload_record
from app.runs.agent_runs import insert_pending_run, update_run_status
from app.storage.uploader import browser_url_for
from app.style.prompt_improver import finalize_hero_triad_prompts
from app.style.resolver import resolve_style_profile, style_profile_to_metadata

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
    compiled_prompts = await finalize_hero_triad_prompts(services, hero_req, style_profile)
    improver_stats = getattr(services, "_last_hero_improver_stats", None)
    metadata_patch: dict[str, Any] = {
        "style_profile": style_profile_to_metadata(style_profile),
        "hero_provider_prompts": [p.to_dict() for p in compiled_prompts],
        "hero_prompt_compiler_version": compiled_prompts[0].compiler_version if compiled_prompts else None,
        "hero_copy_overlay": build_hero_copy_overlay_metadata(hero_req),
        "payload_version": hero_req.payload_version,
    }
    if improver_stats:
        metadata_patch["hero_prompt_improver_stats"] = improver_stats
    await update_run_status(
        pool,
        run_id,
        status="running",
        metadata_patch=metadata_patch,
    )

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


async def _build_poll_response(pool: Any, run_id: uuid.UUID, settings: Any) -> dict[str, Any]:
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
    return out


@router.get("/images/hero-candidates/{run_id}")
async def get_hero_candidates_status(run_id: uuid.UUID, request: Request) -> JSONResponse:
    await require_hmac_get(request)
    services = request.app.state.services
    pool = getattr(services, "pool", None)
    if pool is None:
        return JSONResponse(status_code=503, content={"detail": "database_unavailable"})

    body = await _build_poll_response(pool, run_id, services.settings)
    return JSONResponse(status_code=200, content=body)
