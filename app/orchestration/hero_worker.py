"""Background worker for W21-H hero-candidates (3 homepage heroes, poll-only)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from app.orchestration.pack_worker import (
    _call_generate_single,
    _get_image_provider,
    _style_palette_hex,
    trim_tool_result,
)
from app.payload.hero_models import HeroCandidatesRequest, variant_to_slot
from app.payload.models import PayloadV1
from app.providers.openai_image import ProviderError
from app.providers.retry import RetryExhausted, with_retry
from app.runtime import RuntimeServices
from app.runs.agent_runs import update_run_status
from app.runs.cost_rollup import roll_up_cost
from app.runs.tool_calls import insert_tool_call
from app.storage.asset_writer import (
    insert_pending_asset,
    mark_asset_failed,
    mark_asset_generated,
    mark_asset_uploaded,
)
from app.storage.uploader import AssetObjectMetadata, public_url_for, upload_asset_at_key
from app.style.profile import StyleProfile
from app.style.prompts import build_slot_prompt

logger = logging.getLogger(__name__)


def _resolve_provider_name(request: HeroCandidatesRequest, payload: PayloadV1) -> str:
    if request.default_provider_hint:
        return str(request.default_provider_hint)
    return "google_nano_banana"


async def _finalize_hero_slot(
    pool: Any,
    services: RuntimeServices,
    *,
    run_id: uuid.UUID,
    request: HeroCandidatesRequest,
    style_profile: StyleProfile,
    variant_index: int,
    asset_id: uuid.UUID,
    pr: Any,
    palette_hex: list[str],
) -> str:
    from app.quality.palette_variance import check_palette_drift

    slot = variant_to_slot(request, request.variants[variant_index], variant_index)
    variant = request.variants[variant_index]

    drift, extracted = check_palette_drift(
        pr.image_bytes,
        palette_hex,
        services.settings.palette_drift_threshold,
    )
    ext_id = "" if pr.external_id is None else str(pr.external_id)
    patch: dict[str, Any] | None = None if not drift else {
        "palette_drift": True,
        "palette_extracted": extracted,
    }

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

    r2_key = f"hero-candidates/{run_id}/{variant_index}.png"
    if services.r2 is None:
        r2_url = r2_key
    else:
        await upload_asset_at_key(
            services.r2,
            image_bytes=pr.image_bytes,
            r2_key=r2_key,
            content_type="image/png",
            object_metadata=obj_meta,
        )
        r2_url = public_url_for(services.settings, r2_key)

    await mark_asset_uploaded(pool, asset_id, r2_key=r2_key, r2_url=r2_url)

    hero_meta = {
        "variant_index": variant_index,
        "tone_angle": variant.tone_angle,
        "headline": variant.headline,
        "subhead": variant.subhead,
        "hero_candidate": True,
    }
    if patch:
        hero_meta.update(patch)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE external_media_assets
            SET metadata = COALESCE(metadata, '{}'::jsonb) || $2::jsonb
            WHERE id = $1
            """,
            asset_id,
            json.dumps(hero_meta),
        )

    tm = trim_tool_result({"response_shape": pr.response_shape, "determinism": pr.determinism_level})
    await insert_tool_call(
        pool,
        run_id=run_id,
        tool_name="image_generation",
        args={
            "slot_id": slot.slot_id,
            "variant_index": variant_index,
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


async def run_hero_candidates_in_background(
    services: RuntimeServices,
    *,
    run_id: uuid.UUID,
    request: HeroCandidatesRequest,
    payload: PayloadV1,
    style_profile: StyleProfile,
) -> None:
    sem = getattr(services, "asset_pack_semaphore", None)
    pool = getattr(services, "pool", None)
    if pool is None:
        logger.error("run_hero_candidates_in_background aborted: no pool (run_id=%s)", run_id)
        return
    if sem is None:
        sem = asyncio.Semaphore(services.settings.max_concurrent_packs)

    palette_hex = _style_palette_hex(style_profile)
    pname = _resolve_provider_name(request, payload)
    provider = _get_image_provider(services, pname)

    acquired = False
    await sem.acquire()
    acquired = True
    ok_count = 0
    fail_count = 0

    try:
        for index, variant in enumerate(request.variants):
            slot = variant_to_slot(request, variant, index)
            sp = build_slot_prompt(style_profile, slot)
            dims = (slot.layout.dimensions.w, slot.layout.dimensions.h)
            seed = int(request.base_seed + index)

            pending_meta = {
                "slot_id": slot.slot_id,
                "variant_index": index,
                "slot_intent": slot.intent,
                "style_profile_id": str(style_profile.id),
                "prompt_hash": sp.prompt_hash,
                "seed": seed,
                "determinism_level": "best-effort",
                "run_id": str(run_id),
                "hero_candidate": True,
            }

            asset_id = await insert_pending_asset(
                pool,
                agent_run_id=run_id,
                site_id=request.site_id,
                provider=pname,
                model_version=getattr(provider, "model_version", "unknown"),
                metadata=pending_meta,
            )

            async def attempt(call_seed: int | None) -> Any:
                return await _call_generate_single(
                    provider,
                    slot_id=slot.slot_id,
                    prompt=sp.text,
                    dimensions=dims,
                    seed=call_seed,
                    style_profile=style_profile,
                    reference_images=None,
                )

            try:
                pr = await with_retry(attempt, max_retries=1, base_seed=seed)
            except (RetryExhausted, ProviderError) as exc:
                err = str(getattr(exc, "__cause__", None) or exc)
                await mark_asset_failed(pool, asset_id, error=err)
                tm = trim_tool_result({"error": err})
                await insert_tool_call(
                    pool,
                    run_id=run_id,
                    tool_name="image_generation",
                    args={
                        "slot_id": slot.slot_id,
                        "variant_index": index,
                        "prompt_template_version": sp.prompt_template_version,
                    },
                    result=tm,
                    status="error",
                    latency_ms=0,
                    cost_cents=0,
                    provider=pname,
                    model_version=getattr(provider, "model_version", "unknown"),
                )
                fail_count += 1
                continue

            await _finalize_hero_slot(
                pool,
                services,
                run_id=run_id,
                request=request,
                style_profile=style_profile,
                variant_index=index,
                asset_id=asset_id,
                pr=pr,
                palette_hex=palette_hex,
            )
            ok_count += 1

        await roll_up_cost(pool, run_id)
        if fail_count == 0 and ok_count == 3:
            final = "ok"
        elif ok_count == 0:
            final = "failed"
        else:
            final = "ok"
        await update_run_status(pool, run_id, status=final, finished=True)

    except BaseException as exc:
        logger.exception("run_hero_candidates_in_background failed run_id=%s", run_id)
        try:
            await update_run_status(pool, run_id, status="failed", error=str(exc), finished=True)
        except Exception:
            logger.exception("unable to persist failed hero run status")

    finally:
        if acquired:
            sem.release()
