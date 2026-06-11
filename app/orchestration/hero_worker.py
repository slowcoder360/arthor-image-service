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
from app.payload.hero_models import HeroCandidatesRequest, HeroEditKind, variant_to_slot
from app.payload.models import PayloadV1
from app.providers.openai_image import ProviderError
from app.providers.protocol import ProviderResult
from app.providers.retry import RetryExhausted, with_retry
from app.quality.hero_failure_modes import classify_hero_failure, pick_primary_failure_mode
from app.quality.hero_post_checks import (
    AUTO_RETRY_FAILURE_MODES,
    hero_post_check_failure_mode,
    run_hero_post_checks,
)
from app.style.hero_archetypes import safe_area_inset_pct
from app.style.hero_viewports import resolve_viewport
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
from app.storage.supersession import supersede_asset
from app.storage.uploader import AssetObjectMetadata, public_url_for, upload_asset_at_key
from app.style.profile import StyleProfile
from app.style.hero_prompt_compiler import (
    COMPILER_VERSION,
    CompiledHeroPrompt,
    compile_variant_prompt,
    prompt_text_hash,
)
from app.style.hero_archetypes import resolve_hero_job, resolve_industry
from app.style.hero_visual_strategy import SCENE_CATALOG, SceneArchetypeId
from app.style.hero_reference_plan import build_hero_reference_plan, resolve_reference_bytes_for_plan
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


async def _load_run_metadata(pool: Any, run_id: uuid.UUID) -> dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT metadata FROM agent_runs WHERE id = $1", run_id)
    if row is None:
        return {}
    md = row["metadata"]
    if isinstance(md, str):
        md = json.loads(md)
    return md if isinstance(md, dict) else {}


async def _load_hero_provider_prompts(pool: Any, run_id: uuid.UUID) -> dict[int, dict[str, Any]]:
    md = await _load_run_metadata(pool, run_id)
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


def _hero_safe_inset_pct(request: HeroCandidatesRequest, variant_index: int) -> int:
    variant = request.variants[variant_index]
    inset = safe_area_inset_pct(variant.tone_angle)
    if resolve_viewport(request.hero_viewport) == "mobile" and variant.tone_angle == "offer":
        inset = 45
    return inset


def _hero_post_check_modes(
    request: HeroCandidatesRequest,
    variant_index: int,
    image_bytes: bytes,
) -> list[str]:
    return run_hero_post_checks(
        image_bytes,
        viewport=resolve_viewport(request.hero_viewport),
        safe_area_inset_pct=_hero_safe_inset_pct(request, variant_index),
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
    post_check_modes: list[str] | None = None,
    qa_auto_retried: bool = False,
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
    patch: dict[str, Any] = {}
    if drift:
        patch["palette_drift"] = True
        patch["palette_extracted"] = extracted

    check_modes = list(post_check_modes or [])
    if not prompt_cache_hit and not check_modes:
        check_modes = _hero_post_check_modes(request, variant_index, pr.image_bytes)
    if check_modes:
        patch["hero_post_check_modes"] = check_modes
    if qa_auto_retried:
        patch["qa_auto_retried"] = True

    failure_mode = pick_primary_failure_mode(
        hero_post_check_failure_mode(check_modes),
        classify_hero_failure(None, palette_drift=drift) if drift else None,
    )

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
    if failure_mode:
        hero_meta["failure_mode"] = failure_mode

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
    reference_images: list[bytes] | None = None,
) -> tuple[bool, bool]:
    """Return (success, cache_hit)."""
    dims = (job.slot.layout.dimensions.w, job.slot.layout.dimensions.h)
    cache_hit = False
    use_refs = reference_images if reference_images else None

    if services.settings.hero_prompt_cache_enabled and not use_refs:
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
        use_ref = (
            use_refs
            if (use_refs and getattr(provider, "supports_reference_image", False))
            else None
        )
        return await _call_generate_single(
            provider,
            slot_id=job.slot.slot_id,
            prompt=job.provider_prompt,
            dimensions=dims,
            seed=call_seed,
            style_profile=style_profile,
            reference_images=use_ref,
        )

    qa_auto_retried = False
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

    post_check_modes = _hero_post_check_modes(request, job.index, pr.image_bytes)
    if AUTO_RETRY_FAILURE_MODES.intersection(post_check_modes):
        qa_auto_retried = True
        try:
            pr = await attempt(job.seed + 1)
        except (ProviderError, RetryExhausted):
            pass
        else:
            post_check_modes = _hero_post_check_modes(request, job.index, pr.image_bytes)

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
        post_check_modes=post_check_modes,
        qa_auto_retried=qa_auto_retried,
    )
    return True, cache_hit


def _effective_regenerate_seed(*, original_seed: int, new_seed: int | None) -> int:
    if new_seed is not None:
        return int(new_seed)
    return int(original_seed) + 1


def plan_hero_variant_regenerate(
    request: HeroCandidatesRequest,
    *,
    variant_index: int,
    edit_kind: HeroEditKind,
    style_profile: StyleProfile,
    original_seed: int,
    new_seed: int | None = None,
    prompt_modifier: str | None = None,
    scene_archetype: str | None = None,
    customer_reference_assets: list[Any] | None = None,
) -> tuple[CompiledHeroPrompt, HeroCandidatesRequest, dict[str, Any]]:
    """Resolve provider prompt, seed, and edit metadata for a hero variant regenerate."""
    if variant_index < 0 or variant_index >= len(request.variants):
        raise ValueError("invalid_variant_index")

    req_eff = request
    edit_meta: dict[str, Any] = {"edit_kind": edit_kind, "variant_index": variant_index}
    scene_override: SceneArchetypeId | None = None
    modifier_eff: str | None = None

    if edit_kind == "tweak":
        modifier_eff = str(prompt_modifier or "").strip() or None
        if not modifier_eff:
            raise ValueError("tweak_requires_prompt_modifier")
    elif edit_kind == "reference":
        if not customer_reference_assets:
            raise ValueError("reference_requires_customer_reference_assets")
        req_eff = request.model_copy(
            update={
                "brand_visual": request.brand_visual.model_copy(
                    update={"customer_reference_assets": list(customer_reference_assets)}
                )
            }
        )
        edit_meta["reference_plan"] = build_hero_reference_plan(req_eff)
    elif edit_kind == "rescene":
        archetype = str(scene_archetype or "").strip()
        if archetype not in SCENE_CATALOG:
            raise ValueError("rescene_requires_scene_archetype")
        scene_override = archetype  # type: ignore[assignment]
        edit_meta["scene_archetype"] = archetype

    variant = req_eff.variants[variant_index]
    prompt = compile_variant_prompt(
        req_eff,
        variant,
        variant_index,
        style_profile,
        scene_archetype_override=scene_override,
        prompt_modifier=modifier_eff,
    )
    ctx = resolve_industry(req_eff.business.industry)
    from app.style.hero_visual_strategy import resolve_variant_visual_strategy

    vstrategy = resolve_variant_visual_strategy(req_eff, variant, variant_index)
    slot = variant_to_slot(req_eff, variant, variant_index)
    seed_sp = build_slot_prompt(style_profile, slot)
    seed = _effective_regenerate_seed(original_seed=original_seed, new_seed=new_seed)
    edit_meta["seed"] = seed

    compiled = CompiledHeroPrompt(
        variant_index=variant_index,
        tone_angle=variant.tone_angle,
        prompt=prompt,
        prompt_hash=prompt_text_hash(prompt),
        seed_prompt_hash=seed_sp.prompt_hash,
        compiler_version=COMPILER_VERSION,
        industry_label=ctx.label,
        hero_job=resolve_hero_job(variant.tone_angle),
        hero_viewport=req_eff.hero_viewport,
        scene_archetype=scene_override or vstrategy.scene_archetype,
    )
    return compiled, req_eff, edit_meta


async def run_hero_variant_regenerate_in_background(
    services: RuntimeServices,
    *,
    new_run_id: uuid.UUID,
    old_asset_id: uuid.UUID,
    request: HeroCandidatesRequest,
    style_profile: StyleProfile,
    variant_index: int,
    provider_prompt: str,
    prompt_hash: str,
    seed: int,
    pending_asset_id: uuid.UUID,
    edit_kind: HeroEditKind,
) -> None:
    """Background single-variant hero regenerate — supersedes old asset on success."""
    sem = getattr(services, "asset_pack_semaphore", None)
    pool = getattr(services, "pool", None)
    if pool is None:
        logger.error(
            "run_hero_variant_regenerate_in_background aborted: no pool (run_id=%s)",
            new_run_id,
        )
        return
    if sem is None:
        sem = asyncio.Semaphore(services.settings.max_concurrent_packs)

    pname = "openai_image"
    provider = _get_image_provider(services, pname)
    palette_hex = _style_palette_hex(style_profile)
    variant = request.variants[variant_index]
    slot = variant_to_slot(request, variant, variant_index)

    acquired = False
    await sem.acquire()
    acquired = True
    try:
        job = _VariantJob(
            index=variant_index,
            provider_prompt=provider_prompt,
            prompt_hash=prompt_hash,
            entry={"prompt": provider_prompt, "prompt_hash": prompt_hash},
            asset_id=pending_asset_id,
            slot=slot,
            seed=seed,
        )
        success, _cache = await _generate_one_variant(
            pool,
            services,
            run_id=new_run_id,
            request=request,
            style_profile=style_profile,
            provider=provider,
            pname=pname,
            palette_hex=palette_hex,
            job=job,
        )
        if success:
            await _patch_asset_metadata(
                pool,
                pending_asset_id,
                {"edit_kind": edit_kind, "supersedes_asset_id": str(old_asset_id)},
            )
            await supersede_asset(pool, old_asset_id=old_asset_id, new_asset_id=pending_asset_id)
            await roll_up_cost(pool, new_run_id)
            await update_run_status(pool, new_run_id, status="ok", finished=True)
        else:
            await update_run_status(
                pool,
                new_run_id,
                status="failed",
                error="hero_variant_regenerate_failed",
                finished=True,
            )
    except BaseException as exc:
        logger.exception(
            "run_hero_variant_regenerate_in_background failed run_id=%s", new_run_id
        )
        try:
            await update_run_status(
                pool,
                new_run_id,
                status="failed",
                error=str(exc),
                finished=True,
            )
        except Exception:
            logger.exception("unable to persist failed hero regenerate run status")
    finally:
        if acquired:
            sem.release()


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
    if pname != "openai_image":
        logger.info("hero_candidates forcing openai_image (requested %s)", pname)
        pname = "openai_image"
    provider = _get_image_provider(services, pname)

    acquired = False
    await sem.acquire()
    acquired = True

    try:
        run_md = await _load_run_metadata(pool, run_id)
        reference_plan = run_md.get("reference_plan")
        reference_images: list[bytes] | None = None

        if isinstance(reference_plan, dict) and reference_plan.get("edit_enabled"):

            async def _fetch_url(url: str) -> bytes:
                fetcher = getattr(services, "reference_url_fetcher", None)
                if fetcher is not None:
                    return await fetcher(url)
                import httpx

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    return resp.content

            reference_images, reference_plan = await resolve_reference_bytes_for_plan(
                reference_plan,
                fetch_url=_fetch_url,
            )
            if reference_plan is not None:
                await update_run_status(
                    pool,
                    run_id,
                    status="running",
                    metadata_patch={"reference_plan": reference_plan},
                )
            if not reference_images:
                reference_images = None

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
                    reference_images=reference_images,
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
