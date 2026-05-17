"""POST /images/style-profile/preview — synchronous single probe (s12)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.auth.hmac import require_hmac
from app.payload.idempotency import lookup_idempotency_key
from app.payload.models import (
    PayloadV1,
    Slot,
    SlotCamera,
    SlotCopyContext,
    SlotDimensions,
    SlotLayout,
    SlotLightingMood,
    SlotPeoplePolicy,
    SlotRoute,
    SlotSafeArea,
    SlotSection,
    SlotSubject,
)
from app.payload.repository import IdempotencyConflict, insert_payload_record
from app.payload.validator import validate_payload
from app.providers import registry as providers_registry
from app.providers.openai_image import ProviderError
from app.providers.protocol import ProviderResult
from app.quality.palette_variance import check_palette_drift
from app.runs.agent_runs import insert_pending_run, update_run_status
from app.runs.cost_rollup import roll_up_cost
from app.runs.tool_calls import trim_result as trim_tool_payload
from app.runs.tool_calls import insert_tool_call
from app.storage.asset_writer import (
    insert_pending_asset,
    mark_asset_failed,
    mark_asset_generated,
    mark_asset_uploaded,
)
from app.storage.uploader import AssetObjectMetadata, public_url_for, upload_asset
from app.style.profile import StyleProfile
from app.style.prompts import build_slot_prompt
from app.style.resolver import resolve_style_profile, style_profile_to_metadata

router = APIRouter()


def build_probe_slot(payload: PayloadV1) -> Slot:
    """Canonical style-profile preview probe slot (deterministic).

    Subject line documents the client's industry + city or country fallback.
    """
    locale = payload.location.city or payload.location.country
    primary = f"a representative scene for a {payload.business.industry} in {locale}"
    return Slot(
        slot_id="style_profile_preview",
        ordinal=0,
        page="/",
        route=SlotRoute(name=None, template=None, target_keyword=None),
        section=SlotSection(section_type="style_preview", section_instance_id=None),
        slot_kind="hero",
        intent="canonical style-profile preview probe",
        copy_context=SlotCopyContext(
            page_h1=None,
            section_heading=None,
            body_excerpt=None,
            cta_label=None,
        ),
        subject=SlotSubject(
            primary=primary,
            setting="natural environment",
            props=[],
            people_policy=SlotPeoplePolicy(faces_allowed=False, notes=None),
        ),
        camera=SlotCamera(framing="wide", angle="eye-level", lens_feel="35mm"),
        lighting_mood=SlotLightingMood(mood_tokens=[], contrast="medium"),
        layout=SlotLayout(
            aspect_ratio="1:1",
            dimensions=SlotDimensions(w=1024, h=1024),
            safe_area=SlotSafeArea(mode="center", inset_pct=10),
            overlay_text_risk=False,
        ),
        count=1,
        provider_hint=None,
        condition_on_slot_id=None,
    )


def _preview_provider_name(payload: PayloadV1) -> str:
    if payload.pack.default_provider_hint:
        return str(payload.pack.default_provider_hint)
    return "openai_image"


def _style_palette_hex(style_profile: StyleProfile) -> list[str]:
    out: list[str] = []
    for tone_group in (
        style_profile.palette.light,
        style_profile.palette.dark,
    ):
        out.extend(
            [
                str(tone_group.primary),
                str(tone_group.secondary),
                str(tone_group.background),
                str(tone_group.foreground),
                str(tone_group.muted),
            ]
        )
    return out


def _get_image_provider(services: Any, name: str) -> Any:
    reg = getattr(services, "providers", None)
    if isinstance(reg, dict) and name in reg:
        return reg[name]
    return providers_registry.get_provider(name, services.settings)


async def _call_generate_single(
    provider: Any,
    *,
    slot_id: str | None,
    prompt: str,
    dimensions: tuple[int, int],
    seed: int | None,
    style_profile: StyleProfile,
    reference_images: list[bytes] | None,
) -> ProviderResult:
    kwargs: dict[str, Any] = {
        "prompt": prompt,
        "dimensions": dimensions,
        "seed": seed,
        "style_profile": style_profile,
        "reference_images": reference_images,
    }
    try:
        if slot_id is not None:
            return await provider.generate_single(slot_id=slot_id, **kwargs)
        return await provider.generate_single(**kwargs)
    except TypeError:
        return await provider.generate_single(**kwargs)


def trim_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    return trim_tool_payload(dict(result))


async def _replay_preview(pool: Any, run_id: uuid.UUID) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        ema = await conn.fetchrow(
            """
            SELECT id, r2_url, metadata
            FROM external_media_assets
            WHERE agent_run_id = $1 AND status = 'uploaded'
            ORDER BY created_at ASC
            LIMIT 1
            """,
            run_id,
        )
        if ema is None:
            return None
        tc = await conn.fetchrow(
            """
            SELECT cost_cents, latency_ms
            FROM tool_calls
            WHERE run_id = $1 AND status = 'ok'
            ORDER BY id DESC
            LIMIT 1
            """,
            run_id,
        )

    md = ema["metadata"]
    if isinstance(md, str):
        md = json.loads(md)

    prompt_hash_val = ""
    if isinstance(md, dict):
        prompt_hash_val = str(md.get("prompt_hash", ""))

    cost_cents = int(tc["cost_cents"]) if tc is not None else 0
    latency_ms = int(tc["latency_ms"]) if tc is not None else 0

    return {
        "agent_run_id": str(run_id),
        "asset_id": str(ema["id"]),
        "r2_url": str(ema["r2_url"] or ""),
        "prompt_hash": prompt_hash_val,
        "cost_cents": cost_cents,
        "latency_ms": latency_ms,
    }


async def _finalize_probe_success(
    pool: Any,
    services: Any,
    *,
    run_id: uuid.UUID,
    payload: PayloadV1,
    style_profile: StyleProfile,
    slot: Slot,
    asset_id: uuid.UUID,
    pr: ProviderResult,
    palette_hex: list[str],
) -> str:
    drift, extracted = check_palette_drift(
        pr.image_bytes,
        palette_hex,
        services.settings.palette_drift_threshold,
    )
    ext_id = "" if pr.external_id is None else str(pr.external_id)
    patch: dict[str, Any] | None = (
        None
        if not drift
        else {
            "palette_drift": True,
            "palette_extracted": extracted,
        }
    )

    sp = build_slot_prompt(style_profile, slot)

    await mark_asset_generated(
        pool,
        asset_id,
        width=pr.width,
        height=pr.height,
        bytes_len=len(pr.image_bytes),
        external_id=ext_id,
        metadata_patch=None,
    )

    obj_meta = AssetObjectMetadata(
        run_id=str(run_id),
        slot_id=slot.slot_id,
        agent_run_id=str(run_id),
        provider=pr.provider,
        model_version=pr.model_version,
        prompt_hash=sp.prompt_hash,
        seed=pr.seed,
        style_profile_id=str(style_profile.id),
    )
    if services.r2 is None:
        r2_key = f"arthor-image-service/mock/{payload.site_id}/{asset_id}.png"
        r2_url = r2_key
    else:
        r2_key = await upload_asset(
            services.r2,
            image_bytes=pr.image_bytes,
            site_id=payload.site_id,
            asset_id=asset_id,
            ext="png",
            content_type="image/png",
            object_metadata=obj_meta,
        )
        r2_url = public_url_for(services.settings, r2_key)

    await mark_asset_uploaded(pool, asset_id, r2_key=r2_key, r2_url=r2_url)

    if patch is not None:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE external_media_assets
                SET metadata = COALESCE(metadata, '{}'::jsonb) || $2::jsonb
                WHERE id = $1
                """,
                asset_id,
                json.dumps(patch),
            )

    tm = trim_tool_result(
        {"response_shape": pr.response_shape, "determinism": pr.determinism_level}
    )

    await insert_tool_call(
        pool,
        run_id=run_id,
        tool_name="image_generation",
        args={
            "slot_id": slot.slot_id,
            "prompt_template_version": sp.prompt_template_version,
            "determinism_level": pr.determinism_level,
        },
        result=tm,
        status="ok",
        latency_ms=pr.latency_ms,
        cost_cents=pr.cost_cents,
        provider=pr.provider,
        model_version=pr.model_version,
    )

    return r2_url


@router.post("/images/style-profile/preview")
async def preview_style_profile(request: Request) -> JSONResponse:
    wall0 = time.perf_counter()

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

    pv = payload
    assert pv is not None

    pool = getattr(services, "pool", None)
    if pool is None:
        return JSONResponse(status_code=503, content={"detail": "database_unavailable"})

    prior_run = await lookup_idempotency_key(pool, pv.idempotency_key)
    if prior_run is not None:
        body = await _replay_preview(pool, prior_run)
        if body is not None:
            return JSONResponse(status_code=200, content=body)
        return JSONResponse(
            status_code=409,
            content={"detail": "preview_inflight_or_incomplete"},
        )

    completeness = pv.payload_completeness_score()

    probe_slot = build_probe_slot(pv)

    pname = _preview_provider_name(pv)
    provider = _get_image_provider(services, pname)
    dims = (
        probe_slot.layout.dimensions.w,
        probe_slot.layout.dimensions.h,
    )

    seed = int(pv.pack.base_seed + probe_slot.ordinal)

    run_id = await insert_pending_run(
        pool,
        run_type="image_style_preview",
        site_id=pv.site_id,
        metadata={"payload_completeness_score": completeness},
    )

    try:
        await insert_payload_record(
            pool,
            agent_run_id=run_id,
            payload=pv,
            payload_version=pv.payload_version,
            idempotency_key=pv.idempotency_key,
        )
    except IdempotencyConflict:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
        other_id = await lookup_idempotency_key(pool, pv.idempotency_key)
        if other_id is not None:
            body = await _replay_preview(pool, other_id)
            if body is not None:
                return JSONResponse(status_code=200, content=body)
        raise

    style_profile = await resolve_style_profile(pv)
    await update_run_status(
        pool,
        run_id,
        status="running",
        metadata_patch={"style_profile": style_profile_to_metadata(style_profile)},
    )

    palette_hex = _style_palette_hex(style_profile)
    slot_prompt = build_slot_prompt(style_profile, probe_slot)

    pending_meta = {
        "slot_id": probe_slot.slot_id,
        "slot_intent": probe_slot.intent,
        "style_profile_id": str(style_profile.id),
        "prompt_hash": slot_prompt.prompt_hash,
        "seed": seed,
        "determinism_level": "best-effort",
        "run_id": str(run_id),
    }

    asset_id = await insert_pending_asset(
        pool,
        agent_run_id=run_id,
        site_id=pv.site_id,
        provider=pname,
        model_version=getattr(provider, "model_version", "unknown"),
        metadata=pending_meta,
    )

    try:
        pr = await _call_generate_single(
            provider,
            slot_id=probe_slot.slot_id,
            prompt=slot_prompt.text,
            dimensions=dims,
            seed=seed,
            style_profile=style_profile,
            reference_images=None,
        )
    except ProviderError as exc:
        await mark_asset_failed(pool, asset_id, error=str(exc))
        tm = trim_tool_result({"error": str(exc)})
        await insert_tool_call(
            pool,
            run_id=run_id,
            tool_name="image_generation",
            args={
                "slot_id": probe_slot.slot_id,
                "prompt_template_version": slot_prompt.prompt_template_version,
            },
            result=tm,
            status="error",
            latency_ms=0,
            cost_cents=0,
            provider=pname,
            model_version=getattr(provider, "model_version", "unknown"),
        )
        await roll_up_cost(pool, run_id)
        await update_run_status(
            pool,
            run_id,
            status="failed",
            error="provider_error",
            finished=True,
        )
        return JSONResponse(
            status_code=502,
            content={"error": "provider_error", "retry": False},
        )

    r2_url_out = await _finalize_probe_success(
        pool,
        services,
        run_id=run_id,
        payload=pv,
        style_profile=style_profile,
        slot=probe_slot,
        asset_id=asset_id,
        pr=pr,
        palette_hex=palette_hex,
    )

    await roll_up_cost(pool, run_id)
    await update_run_status(pool, run_id, status="ok", finished=True)

    wall_ms = int((time.perf_counter() - wall0) * 1000)

    return JSONResponse(
        status_code=200,
        content={
            "agent_run_id": str(run_id),
            "asset_id": str(asset_id),
            "r2_url": r2_url_out,
            "prompt_hash": slot_prompt.prompt_hash,
            "cost_cents": pr.cost_cents,
            "latency_ms": wall_ms,
        },
    )

