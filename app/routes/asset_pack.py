"""Asset-pack HTTP entrypoint."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.auth.hmac import require_hmac
from app.orchestration.pack_worker import run_in_background
from app.payload.idempotency import lookup_idempotency_key
from app.payload.repository import insert_payload_record
from app.payload.validator import validate_payload
from app.runs.agent_runs import insert_pending_run, update_run_status
from app.style.resolver import resolve_style_profile, style_profile_to_metadata

router = APIRouter()


@router.post("/images/asset-pack/generate")
async def generate_asset_pack(request: Request) -> JSONResponse:
    raw = await require_hmac(request)
    services = request.app.state.services
    payload, report = validate_payload(raw)

    if report.errors:
        return JSONResponse(
            status_code=400,
            content={
                "errors": report.errors,
                "warnings": report.warnings,
                "completeness_score": report.completeness_score,
            },
        )

    pool = getattr(services, "pool", None)
    if pool is None:
        return JSONResponse(status_code=503, content={"detail": "database_unavailable"})

    payload_v = payload
    assert payload_v is not None

    maybe_existing = await lookup_idempotency_key(pool, payload_v.idempotency_key)
    if maybe_existing is not None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status FROM agent_runs WHERE id = $1",
                maybe_existing,
            )
        status = str(row["status"]) if row is not None else "running"
        return JSONResponse(
            status_code=200,
            content={
                "agent_run_id": str(maybe_existing),
                "status": status,
                "idempotent_replay": True,
            },
        )

    completeness = payload_v.payload_completeness_score()
    run_id = await insert_pending_run(
        pool,
        run_type="image_pack_generation",
        site_id=payload_v.site_id,
        metadata={"payload_completeness_score": completeness},
    )

    await insert_payload_record(
        pool,
        agent_run_id=run_id,
        payload=payload_v,
        payload_version=payload_v.payload_version,
        idempotency_key=payload_v.idempotency_key,
    )

    style_profile = await resolve_style_profile(payload_v)
    await update_run_status(
        pool,
        run_id,
        status="running",
        metadata_patch={"style_profile": style_profile_to_metadata(style_profile)},
    )

    asyncio.create_task(
        run_in_background(
            services,
            run_id=run_id,
            payload=payload_v,
            style_profile=style_profile,
        )
    )

    return JSONResponse(
        status_code=202,
        content={"agent_run_id": str(run_id), "status": "accepted"},
    )
