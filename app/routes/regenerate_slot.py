"""Single-slot regeneration HTTP entrypoint (s11).

POST /images/regenerate-slot accepts a previously uploaded asset id plus either a new seed
and/or prompt modifier. Idempotency is **not** supported in v1 — each request creates a new run.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import UUID4, BaseModel, ValidationError

from app.auth.hmac import require_hmac
from app.orchestration.pack_worker import (
    get_image_provider_for_services,
    resolve_provider_for_slot,
    run_single_slot_in_background,
    slot_with_prompt_modifier_overlay,
)
from app.payload.models import PayloadV1
from app.storage.asset_writer import insert_pending_asset
from app.style.prompts import build_slot_prompt
from app.runs.agent_runs import insert_pending_run
from app.runtime import RuntimeServices
from app.style.profile import StyleProfile
from app.style.resolver import resolve_style_profile, style_profile_to_metadata

router = APIRouter()


class RegenerateSlotBody(BaseModel):
    asset_id: UUID4
    new_seed: int | None = None
    new_prompt_modifier: str | None = None


def _metadata_as_dict(meta: Any) -> dict[str, Any]:
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str):
        return json.loads(meta)
    return dict(meta)


async def _style_profile_from_original_run(
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


def _original_asset_seed(asset_meta: dict[str, Any], payload: PayloadV1, slot) -> int:
    raw = asset_meta.get("seed")
    if raw is not None:
        return int(raw)
    return int(payload.pack.base_seed + slot.ordinal)


@router.post("/images/regenerate-slot")
async def regenerate_slot(request: Request) -> JSONResponse:
    raw = await require_hmac(request)
    services: RuntimeServices = request.app.state.services
    pool = getattr(services, "pool", None)
    if pool is None:
        return JSONResponse(status_code=503, content={"detail": "database_unavailable"})

    try:
        body = RegenerateSlotBody.model_validate(json.loads(raw.decode()))
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    if body.new_seed is None and (
        body.new_prompt_modifier is None or not str(body.new_prompt_modifier).strip()
    ):
        return JSONResponse(
            status_code=400,
            content={"detail": "provide new_seed and/or new_prompt_modifier"},
        )

    modifier_eff = (
        None
        if body.new_prompt_modifier is None
        else str(body.new_prompt_modifier).strip() or None
    )

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
            return JSONResponse(
                status_code=400,
                content={"detail": "asset_must_be_uploaded"},
            )

        payload_row = await conn.fetchrow(
            """
            SELECT payload
            FROM image_request_payloads
            WHERE agent_run_id = $1
            """,
            asset_row["agent_run_id"],
        )
        if payload_row is None:
            return JSONResponse(
                status_code=400,
                content={"detail": "original_payload_missing"},
            )

        payload_v = PayloadV1.model_validate(payload_row["payload"])
        asset_meta = _metadata_as_dict(asset_row["metadata"])
        slot_id = asset_meta.get("slot_id")
        if not slot_id:
            return JSONResponse(status_code=400, content={"detail": "asset_missing_slot_id"})

        slot = next((s for s in payload_v.slots if s.slot_id == str(slot_id)), None)
        if slot is None:
            return JSONResponse(status_code=400, content={"detail": "slot_not_in_payload"})

        style_profile = await _style_profile_from_original_run(
            pool,
            original_run_id=asset_row["agent_run_id"],
            payload=payload_v,
        )

    slot_eff = slot_with_prompt_modifier_overlay(slot, modifier_eff)
    seed_eff = (
        int(body.new_seed)
        if body.new_seed is not None
        else _original_asset_seed(asset_meta, payload_v, slot) + 1
    )

    pname = resolve_provider_for_slot(payload_v, slot_eff)
    provider = get_image_provider_for_services(services, pname)
    sp = build_slot_prompt(style_profile, slot_eff)
    pending_meta = {
        "slot_id": slot_eff.slot_id,
        "slot_intent": slot_eff.intent,
        "style_profile_id": str(style_profile.id),
        "prompt_hash": sp.prompt_hash,
        "seed": int(seed_eff),
        "determinism_level": "best-effort",
        "run_id": "",  # patched below
    }

    new_run_id = await insert_pending_run(
        pool,
        run_type="image_slot_regenerate",
        site_id=payload_v.site_id,
        parent_run_id=asset_row["agent_run_id"],
        metadata={
            "original_asset_id": str(body.asset_id),
            "style_profile": style_profile_to_metadata(style_profile),
        },
    )
    pending_meta["run_id"] = str(new_run_id)

    new_asset_id = await insert_pending_asset(
        pool,
        agent_run_id=new_run_id,
        site_id=payload_v.site_id,
        provider=pname,
        model_version=getattr(provider, "model_version", "unknown"),
        metadata=pending_meta,
    )

    asyncio.create_task(
        run_single_slot_in_background(
            services,
            new_run_id=new_run_id,
            slot=slot,
            style_profile=style_profile,
            seed=seed_eff,
            prompt_modifier_text=modifier_eff,
            old_asset_id=body.asset_id,
            payload=payload_v,
            pending_asset_id=new_asset_id,
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
