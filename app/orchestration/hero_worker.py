"""Background worker for W21-H hero-candidates (3 homepage heroes, poll-only)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
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
from app.providers.protocol import ProviderResult
from app.providers.retry import RetryExhausted, with_retry
from app.quality.hero_failure_modes import classify_hero_failure
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
from app.style.hero_prompt_compiler import prompt_text_hash
from app.style.prompts import PROMPT_TEMPLATE_VERSION, build_slot_prompt

logger = logging.getLogger(__name__)


@dataclass
class _VariantJob:
    index: int
    provider_prompt: str
    prompt_hash: str
    entry: dict[str, Any] | None
    asset_id: uuid.UUID
    slot: Any
    seed: int


async def _load_hero_provider_prompts(pool: Any, run_id: uuid.UUID) -> dict[int, dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT metadata FROM agent_runs WHERE id = $1", run_id)
    if row is None:
        return {}
    md = row["metadata"]
    if isinstance(md, str):
        md = json.loads(md)
    if not isinstance(md, dict):
        return {}
    raw = md.get("hero_provider_prompts") or []
    out: dict[int, dict[str, Any]] = {}
    for item in raw:
        if isinstance(item, dict) and "variant_index" in item:
            out[int(item["variant_index"])] = item
    return out


def _resolve_provider_name(
    request: HeroCandidatesRequest,
    payload: PayloadV1,
    settings: Any,
) -> str:
    if request.default_provider_hint:
        return str(request.default_provider_hint)
    return str(getattr(settings, "hero_default_provider", "openai_image"))


async def _find_cached_hero_asset(
    pool: Any,
    *,
    site_id: uuid.UUID,
    prompt_hash: str,
    provider: str,
) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT r2_key, r2_url, width, height, metadata
            FROM external_media_assets
            WHERE site_id = $1
              AND provider = $2
              AND status = 'uploaded'
              AND metadata->>'prompt_hash' = $3
              AND metadata->>'hero_candidate' = 'true'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            site_id,
            provider,
            prompt_hash,
        )
    if row is None:
        return None
    md = row["metadata"]
    if isinstance(md, str):
        md = json.loads(md)
    return {
        "r2_key": row["r2_key"],
        "r2_url": row["r2_url"],
        "width": row["width"],
        "height": row["height"],
        "metadata": md if isinstance(md, dict) else {},
    }


async def _patch_asset_metadata(pool: Any, asset_id: uuid.UUID, patch: dict[str, Any]) -> None:
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


async def _finalize_hero_slot(
    pool: Any,
    services: RuntimeServices,
    *,
    run_id: uuid.UUID,
    request: HeroCandidatesRequest,
    style_profile: StyleProfile,
    variant_index: int,
    asset_id: uuid.UUID,
    pr: ProviderResult,
    palette_hex: list[str],
    prompt_hash: str,
    prompt_cache_hit: bool = False,
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
        prompt_hash=prompt_hash,
        seed=pr.seed,
        style_profile_id=str(style_profile.id),
    )

    r2_key = f"hero-candidates/{run_id}/{variant_index}.png"
    if prompt_cache_hit and pr.response_shape.get("cached_r2_key"):
        r2_key = str(pr.response_shape["cached_r2_key"])
        r2_url = str(pr.response_shape.get("cached_r2_url") or public_url_for(services.settings, r2_key))
    elif services.r2 is None:
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

    hero_meta: dict[str, Any] = {
        "variant_index": variant_index,
        "tone_angle": variant.tone_angle,
        "headline": variant.headline,
        "subhead": variant.subhead,
        "hero_candidate": True,
    }
    if prompt_cache_hit:
        hero_meta["prompt_cache_hit"] = True
    if patch:
        hero_meta.update(patch)
        hero_meta["failure_mode"] = classify_hero_failure(None, palette_drift=True)

    await _patch_asset_metadata(pool, asset_id, hero_meta)

    tm = trim_tool_result({
        "response_shape": pr.response_shape,
        "determinism": pr.determinism_level,
        "prompt_cache_hit": prompt_cache_hit,
    })
    await insert_tool_call(
        pool,
        run_id=run_id,
        tool_name="image_generation",
        args={
            "slot_id": slot.slot_id,
            "variant_index": variant_index,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            "determinism_level": pr.determinism_level,
            "prompt_cache_hit": prompt_cache_hit,
        },
        result=tm,
        status="ok",
        latency_ms=pr.latency_ms,
        cost_cents=0 if prompt_cache_hit else pr.cost_cents,
        provider=pr.provider,
        model_version=pr.model_version,
    )
    return r2_url


async def _generate_one_variant(
    pool: Any,
    services: RuntimeServices,
    *,
    run_id: uuid.UUID,
    request: HeroCandidatesRequest,
    style_profile: StyleProfile,
    provider: Any,
    pname: str,
    palette_hex: list[str],
    job: _VariantJob,
) -> tuple[bool, bool]:
    """Return (success, cache_hit)."""
    dims = (job.slot.layout.dimensions.w, job.slot.layout.dimensions.h)
    cache_hit = False

    if services.settings.hero_prompt_cache_enabled:
        cached = await _find_cached_hero_asset(
            pool,
            site_id=request.site_id,
            prompt_hash=job.prompt_hash,
            provider=pname,
        )
        if cached and cached.get("r2_key"):
            cached_key = str(cached["r2_key"])
            image_bytes = b"\x89PNGcached"
            pr = ProviderResult(
                image_bytes=image_bytes,
                width=int(cached.get("width") or dims[0]),
                height=int(cached.get("height") or dims[1]),
                seed=job.seed,
                provider=pname,
                model_version=getattr(provider, "model_version", "unknown"),
                cost_cents=0,
                latency_ms=1,
                external_id=None,
                response_shape={
                    "cached_r2_key": cached_key,
                    "cached_r2_url": cached.get("r2_url"),
                },
                determinism_level="best-effort",
            )
            cache_hit = True
            await _finalize_hero_slot(
                pool,
                services,
                run_id=run_id,
                request=request,
                style_profile=style_profile,
                variant_index=job.index,
                asset_id=job.asset_id,
                pr=pr,
                palette_hex=palette_hex,
                prompt_hash=job.prompt_hash,
                prompt_cache_hit=True,
            )
            return True, cache_hit

    async def attempt(call_seed: int | None) -> ProviderResult:
        return await _call_generate_single(
            provider,
            slot_id=job.slot.slot_id,
            prompt=job.provider_prompt,
            dimensions=dims,
            seed=call_seed,
            style_profile=style_profile,
            reference_images=None,
        )

    try:
        pr = await with_retry(attempt, max_retries=1, base_seed=job.seed)
    except (RetryExhausted, ProviderError) as exc:
        err = str(getattr(exc, "__cause__", None) or exc)
        failure_mode = classify_hero_failure(err)
        await mark_asset_failed(pool, job.asset_id, error=err)
        await _patch_asset_metadata(
            pool,
            job.asset_id,
            {"failure_mode": failure_mode, "variant_index": job.index},
        )
        tm = trim_tool_result({"error": err, "failure_mode": failure_mode})
        await insert_tool_call(
            pool,
            run_id=run_id,
            tool_name="image_generation",
            args={
                "slot_id": job.slot.slot_id,
                "variant_index": job.index,
                "prompt_template_version": PROMPT_TEMPLATE_VERSION,
                "failure_mode": failure_mode,
            },
            result=tm,
            status="error",
            latency_ms=0,
            cost_cents=0,
            provider=pname,
            model_version=getattr(provider, "model_version", "unknown"),
        )
        return False, False

    await _finalize_hero_slot(
        pool,
        services,
        run_id=run_id,
        request=request,
        style_profile=style_profile,
        variant_index=job.index,
        asset_id=job.asset_id,
        pr=pr,
        palette_hex=palette_hex,
        prompt_hash=job.prompt_hash,
    )
    return True, cache_hit


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
    pname = _resolve_provider_name(request, payload, services.settings)
    provider = _get_image_provider(services, pname)

    acquired = False
    await sem.acquire()
    acquired = True

    try:
        precompiled = await _load_hero_provider_prompts(pool, run_id)
        jobs: list[_VariantJob] = []
        for index, variant in enumerate(request.variants):
            slot = variant_to_slot(request, variant, index)
            sp = build_slot_prompt(style_profile, slot)
            entry = precompiled.get(index)
            if entry and entry.get("prompt"):
                provider_prompt = str(entry["prompt"])
                prompt_hash = str(entry.get("prompt_hash") or prompt_text_hash(provider_prompt))
            else:
                provider_prompt = sp.text
                prompt_hash = sp.prompt_hash
            seed = int(request.base_seed + index)

            pending_meta: dict[str, Any] = {
                "slot_id": slot.slot_id,
                "variant_index": index,
                "slot_intent": slot.intent,
                "style_profile_id": str(style_profile.id),
                "prompt_hash": prompt_hash,
                "seed": seed,
                "determinism_level": "best-effort",
                "run_id": str(run_id),
                "hero_candidate": True,
            }
            if entry:
                for key in ("compiler_version", "industry_label", "seed_prompt_hash"):
                    if entry.get(key):
                        pending_meta[key] = entry[key]

            asset_id = await insert_pending_asset(
                pool,
                agent_run_id=run_id,
                site_id=request.site_id,
                provider=pname,
                model_version=getattr(provider, "model_version", "unknown"),
                metadata=pending_meta,
            )
            jobs.append(
                _VariantJob(
                    index=index,
                    provider_prompt=provider_prompt,
                    prompt_hash=prompt_hash,
                    entry=entry,
                    asset_id=asset_id,
                    slot=slot,
                    seed=seed,
                )
            )

        results = await asyncio.gather(
            *[
                _generate_one_variant(
                    pool,
                    services,
                    run_id=run_id,
                    request=request,
                    style_profile=style_profile,
                    provider=provider,
                    pname=pname,
                    palette_hex=palette_hex,
                    job=job,
                )
                for job in jobs
            ],
            return_exceptions=True,
        )

        ok_count = 0
        fail_count = 0
        for result in results:
            if isinstance(result, BaseException):
                logger.exception("hero variant task failed: %s", result)
                fail_count += 1
                continue
            success, _cache = result
            if success:
                ok_count += 1
            else:
                fail_count += 1

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
