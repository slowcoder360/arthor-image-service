"""Background asset-pack orchestration (s10 spine)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from types import SimpleNamespace
from typing import Any

from app.callback.client import send_completion_callback
from app.payload.models import PayloadV1, Slot
from app.providers import get_provider
from app.providers.openai_image import ProviderError
from app.providers.protocol import ProviderResult
from app.providers.retry import RetryExhausted, with_retry
from app.quality.palette_variance import check_palette_drift
from app.runtime import RuntimeServices
from app.runs.agent_runs import update_run_status
from app.runs.cost_rollup import roll_up_cost
from app.runs.tool_calls import insert_tool_call
from app.runs.tool_calls import trim_result as trim_tool_payload
from app.storage.asset_writer import mark_asset_failed, mark_asset_generated, mark_asset_uploaded
from app.storage.asset_writer import insert_pending_asset
from app.storage.supersession import supersede_asset
from app.storage.uploader import AssetObjectMetadata, public_url_for, upload_asset
from app.style.prompts import build_slot_prompt
from app.style.profile import StyleProfile

logger = logging.getLogger(__name__)


def _generation_slot_order(payload: PayloadV1) -> list[Slot]:
    slots_by_id = {s.slot_id: s for s in payload.slots}
    hero = payload.pack.reference_policy.hero_slot_id
    ordered_ids: list[str] = []
    seen: set[str] = set()

    def add(sid: str) -> None:
        if sid in slots_by_id and sid not in seen:
            ordered_ids.append(sid)
            seen.add(sid)

    if hero:
        add(hero)
    for sid in payload.pack.slot_order:
        add(sid)
    for s in payload.slots:
        add(s.slot_id)
    return [slots_by_id[sid] for sid in ordered_ids]


def _resolve_provider_name(payload: PayloadV1, slot: Slot) -> str:
    if payload.pack.default_provider_hint:
        return str(payload.pack.default_provider_hint)
    if slot.provider_hint:
        return str(slot.provider_hint)
    if slot.slot_kind == "og":
        return "openai_image"
    return "google_nano_banana"


def _get_image_provider(services: RuntimeServices, name: str) -> Any:
    reg = getattr(services, "providers", None)
    if isinstance(reg, dict) and name in reg:
        return reg[name]
    return get_provider(name, services.settings)


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


def _reference_bytes_for_slot(payload: PayloadV1, hero_id: str, slot: Slot, hero_bytes: bytes | None):
    policy = payload.pack.reference_policy
    if not policy.condition_non_hero_slots_on_hero:
        return None
    if slot.slot_id == hero_id:
        return None
    if slot.condition_on_slot_id != hero_id:
        return None
    return None if hero_bytes is None else [hero_bytes]


def trim_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    return trim_tool_payload(dict(result))


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


async def _finalize_slot_success(
    pool: Any,
    services: RuntimeServices,
    *,
    run_id: uuid.UUID,
    payload: PayloadV1 | None,
    style_profile: StyleProfile,
    slot: Slot,
    asset_id: uuid.UUID,
    pr: ProviderResult,
    palette_hex: list[str],
    site_id: uuid.UUID | None = None,
) -> None:
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

    effective_site_id = (
        site_id if site_id is not None else (payload.site_id if payload is not None else None)
    )
    if effective_site_id is None:
        raise ValueError("_finalize_slot_success requires site_id or payload with site_id")

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
        prompt_hash=build_slot_prompt(style_profile, slot).prompt_hash,
        seed=pr.seed,
        style_profile_id=str(style_profile.id),
    )
    if services.r2 is None:
        r2_key = f"arthor-image-service/mock/{effective_site_id}/{asset_id}.png"
        r2_url = r2_key
    else:
        r2_key = await upload_asset(
            services.r2,
            image_bytes=pr.image_bytes,
            site_id=effective_site_id,
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

    tm = trim_tool_result({"response_shape": pr.response_shape, "determinism": pr.determinism_level})

    await insert_tool_call(
        pool,
        run_id=run_id,
        tool_name="image_generation",
        args={
            "slot_id": slot.slot_id,
            "prompt_template_version": build_slot_prompt(
                style_profile, slot
            ).prompt_template_version,
            "determinism_level": pr.determinism_level,
        },
        result=tm,
        status="ok",
        latency_ms=pr.latency_ms,
        cost_cents=pr.cost_cents,
        provider=pr.provider,
        model_version=pr.model_version,
    )


async def _emit_callback(
    services: RuntimeServices,
    *,
    payload: PayloadV1,
    run_id: uuid.UUID,
    duration_seconds: float,
    asset_summaries: list[dict[str, Any]],
    pack_status: str,
    total_cost_cents: int,
) -> None:
    cb = getattr(services, "callback_client", None)
    body = {
        "agent_run_id": str(run_id),
        "site_id": str(payload.site_id),
        "status": pack_status,
        "assets": asset_summaries,
        "total_cost_cents": int(total_cost_cents),
        "duration_seconds": float(duration_seconds),
    }
    secret = getattr(services.settings, "fastapi_arthor_shared_secret", None) or ""
    callback_url_str = str(payload.callback_url)

    if cb is not None:
        await cb.send_completion_callback(callback_url_str, body, secret=secret)
        return

    import httpx

    def factory() -> Any:
        return httpx.AsyncClient(timeout=120.0)

    await send_completion_callback(
        callback_url=callback_url_str,
        body=body,
        secret=secret,
        client_factory=factory,
    )


async def _run_slot_generate_single(
    pool: Any,
    services: RuntimeServices,
    *,
    run_id: uuid.UUID,
    payload: PayloadV1,
    style_profile: StyleProfile,
    slot: Slot,
    hero_id: str,
    hero_bytes: bytes | None,
    palette_hex: list[str],
) -> tuple[
    dict[str, Any],
    str,
    ProviderResult | None,
]:
    """Returns (callback asset dict, status ok|failed, provider result when ok)."""

    pname = _resolve_provider_name(payload, slot)
    provider = _get_image_provider(services, pname)
    sp = build_slot_prompt(style_profile, slot)
    dims = (slot.layout.dimensions.w, slot.layout.dimensions.h)
    refs = _reference_bytes_for_slot(payload, hero_id, slot, hero_bytes)
    wants_ref = bool(refs)

    async def attempt(call_seed: int | None) -> ProviderResult:
        use_ref = (
            refs if (wants_ref and getattr(provider, "supports_reference_image", False)) else None
        )
        return await _call_generate_single(
            provider,
            slot_id=slot.slot_id,
            prompt=sp.text,
            dimensions=dims,
            seed=call_seed,
            style_profile=style_profile,
            reference_images=use_ref,
        )

    pending_meta = {
        "slot_id": slot.slot_id,
        "slot_intent": slot.intent,
        "style_profile_id": str(style_profile.id),
        "prompt_hash": sp.prompt_hash,
        "seed": int(payload.pack.base_seed + slot.ordinal),
        "determinism_level": "best-effort",
        "run_id": str(run_id),
    }

    asset_id = await insert_pending_asset(
        pool,
        agent_run_id=run_id,
        site_id=payload.site_id,
        provider=pname,
        model_version=getattr(provider, "model_version", "unknown"),
        metadata=pending_meta,
    )

    try:
        pr = await with_retry(
            attempt,
            max_retries=1,
            base_seed=int(payload.pack.base_seed + slot.ordinal),
        )
    except RetryExhausted as rex:
        err = str(rex.__cause__ or rex)
        await mark_asset_failed(pool, asset_id, error=err)
        tm = trim_tool_result({"error": err})
        await insert_tool_call(
            pool,
            run_id=run_id,
            tool_name="image_generation",
            args={
                "slot_id": slot.slot_id,
                "prompt_template_version": sp.prompt_template_version,
            },
            result=tm,
            status="error",
            latency_ms=0,
            cost_cents=0,
            provider=pname,
            model_version=getattr(provider, "model_version", "unknown"),
        )
        summary = {"slot_id": slot.slot_id, "asset_id": str(asset_id), "status": "failed"}
        return summary, "failed", None

    await _finalize_slot_success(
        pool,
        services,
        run_id=run_id,
        payload=payload,
        style_profile=style_profile,
        slot=slot,
        asset_id=asset_id,
        pr=pr,
        palette_hex=palette_hex,
    )
    summary = {"slot_id": slot.slot_id, "asset_id": str(asset_id), "status": "uploaded"}
    return summary, "ok", pr


async def _maybe_generate_pack_consistent(
    pool: Any,
    services: RuntimeServices,
    *,
    provider: Any,
    run_id: uuid.UUID,
    payload: PayloadV1,
    style_profile: StyleProfile,
    remainder: list[Slot],
    palette_hex: list[str],
) -> list[dict[str, Any]] | None:
    prompt_objs = []
    for slot in remainder:
        sprompt = build_slot_prompt(style_profile, slot)
        prompt_objs.append(
            SimpleNamespace(
                text=sprompt.text,
                dimensions=(slot.layout.dimensions.w, slot.layout.dimensions.h),
            )
        )
    pending_by_slot: dict[str, uuid.UUID] = {}
    for slot in remainder:
        sprompt = build_slot_prompt(style_profile, slot)
        pending_meta = {
            "slot_id": slot.slot_id,
            "slot_intent": slot.intent,
            "style_profile_id": str(style_profile.id),
            "prompt_hash": sprompt.prompt_hash,
            "seed": int(payload.pack.base_seed + slot.ordinal),
            "determinism_level": "best-effort",
            "run_id": str(run_id),
        }
        aid = await insert_pending_asset(
            pool,
            agent_run_id=run_id,
            site_id=payload.site_id,
            provider=_resolve_provider_name(payload, slot),
            model_version=getattr(provider, "model_version", "unknown"),
            metadata=pending_meta,
        )
        pending_by_slot[slot.slot_id] = aid

    try:
        seed = payload.pack.base_seed + min(slot.ordinal for slot in remainder)
        results = await provider.generate_pack_consistent(
            prompts=prompt_objs,
            style_profile=style_profile,
            seed=seed,
        )
    except ProviderError:
        for aid in pending_by_slot.values():
            await mark_asset_failed(pool, aid, error="batch_path_aborted_retry_per_slot")
        return None

    summaries: list[dict[str, Any]] = []
    for slot, pr in zip(remainder, results, strict=True):
        aid = pending_by_slot[slot.slot_id]
        await _finalize_slot_success(
            pool,
            services,
            run_id=run_id,
            payload=payload,
            style_profile=style_profile,
            slot=slot,
            asset_id=aid,
            pr=pr,
            palette_hex=palette_hex,
        )
        summaries.append({"slot_id": slot.slot_id, "asset_id": str(aid), "status": "uploaded"})
    return summaries


async def run_in_background(
    services: RuntimeServices,
    *,
    run_id: uuid.UUID,
    payload: PayloadV1,
    style_profile: StyleProfile,
) -> None:
    sem = getattr(services, "asset_pack_semaphore", None)
    pool = getattr(services, "pool", None)
    if pool is None:
        logger.error("run_in_background aborted: DB pool unavailable (run_id=%s)", run_id)
        return
    if sem is None:
        sem = asyncio.Semaphore(services.settings.max_concurrent_packs)

    palette_hex = _style_palette_hex(style_profile)

    hero_id = payload.pack.reference_policy.hero_slot_id
    ordered_slots = _generation_slot_order(payload)
    if not ordered_slots:
        logger.error("run_in_background: empty slot list")
        await update_run_status(
            pool,
            run_id,
            status="failed",
            error="empty_slot_list",
            finished=True,
        )
        return

    t0_mono = time.perf_counter()
    acquired = False
    await sem.acquire()
    acquired = True
    try:
        summaries: list[dict[str, Any]] = []

        hero_bytes: bytes | None = None

        hero_slot = ordered_slots[0]
        h_summary, _, hero_pr = await _run_slot_generate_single(
            pool,
            services,
            run_id=run_id,
            payload=payload,
            style_profile=style_profile,
            slot=hero_slot,
            hero_id=hero_id,
            hero_bytes=None,
            palette_hex=palette_hex,
        )
        summaries.append(h_summary)
        if hero_pr is not None and hero_slot.slot_id == hero_id:
            hero_bytes = hero_pr.image_bytes

        remainder = [s for s in ordered_slots[1:] if s.slot_id != hero_id]

        batch_provider: Any | None = None
        if remainder:
            names = {_resolve_provider_name(payload, s) for s in remainder}
            if len(names) == 1:
                p0 = _get_image_provider(services, next(iter(names)))
                if getattr(p0, "supports_pack_consistent", False):
                    batch_provider = p0

        if batch_provider is not None and remainder:
            batch_out = await _maybe_generate_pack_consistent(
                pool,
                services,
                provider=batch_provider,
                run_id=run_id,
                payload=payload,
                style_profile=style_profile,
                remainder=remainder,
                palette_hex=palette_hex,
            )
            if batch_out is None:
                for slot in remainder:
                    summary, _, _pr = await _run_slot_generate_single(
                        pool,
                        services,
                        run_id=run_id,
                        payload=payload,
                        style_profile=style_profile,
                        slot=slot,
                        hero_id=hero_id,
                        hero_bytes=hero_bytes,
                        palette_hex=palette_hex,
                    )
                    summaries.append(summary)
            else:
                summaries.extend(batch_out)
        else:
            for slot in remainder:
                summary, _, _pr = await _run_slot_generate_single(
                    pool,
                    services,
                    run_id=run_id,
                    payload=payload,
                    style_profile=style_profile,
                    slot=slot,
                    hero_id=hero_id,
                    hero_bytes=hero_bytes,
                    palette_hex=palette_hex,
                )
                summaries.append(summary)

        ok_count = fail_count = 0
        for s in summaries:
            st = s.get("status", "")
            if st == "uploaded":
                ok_count += 1
            else:
                fail_count += 1

        total_cost_cents = await roll_up_cost(pool, run_id)
        await update_run_status(pool, run_id, status="ok", finished=True)

        if fail_count == 0:
            pack_status = "complete"
        elif ok_count == 0:
            pack_status = "failed"
        else:
            pack_status = "partial"

        duration_seconds = round(time.perf_counter() - t0_mono, 3)
        try:
            await _emit_callback(
                services,
                payload=payload,
                run_id=run_id,
                duration_seconds=duration_seconds,
                asset_summaries=summaries,
                pack_status=pack_status,
                total_cost_cents=total_cost_cents,
            )
        except Exception:
            logger.warning(
                "completion callback failed (non-fatal) run_id=%s",
                run_id,
                exc_info=True,
            )

    except BaseException as exc:
        logger.exception("run_in_background failed run_id=%s", run_id)
        try:
            await update_run_status(pool, run_id, status="failed", error=str(exc), finished=True)
        except Exception:
            logger.exception("unable to persist failed agent_run status")

    finally:
        if acquired:
            sem.release()


def slot_with_prompt_modifier_overlay(slot: Slot, modifier: str | None) -> Slot:
    """Overlay ``modifier`` onto ``slot.intent`` using `` — Adjust: …`` (s11 inspector convention)."""

    if modifier is None:
        return slot
    adj = str(modifier).strip()
    if not adj:
        return slot
    new_intent = f"{slot.intent} — Adjust: {adj}"
    return slot.model_copy(update={"intent": new_intent})


def resolve_provider_for_slot(payload: PayloadV1 | None, slot: Slot) -> str:
    """Resolve provider name for a slot; ``payload`` may be omitted (worker-only tests)."""

    if payload is not None:
        return _resolve_provider_name(payload, slot)
    if slot.provider_hint:
        return str(slot.provider_hint)
    if slot.slot_kind == "og":
        return "openai_image"
    return "google_nano_banana"


def get_image_provider_for_services(services: RuntimeServices, name: str) -> Any:
    return _get_image_provider(services, name)


async def run_single_slot_in_background(
    services: RuntimeServices,
    *,
    new_run_id: uuid.UUID,
    slot: Slot,
    style_profile: StyleProfile,
    seed: int,
    prompt_modifier_text: str | None,
    old_asset_id: uuid.UUID,
    payload: PayloadV1 | None = None,
    pending_asset_id: uuid.UUID | None = None,
) -> None:
    """Background single-slot regeneration (s11).

    Mirrors ``run_in_background`` lifecycle for one slot: pending → generate → upload → tool_call.
    Supersedes ``old_asset_id`` after success. Does **not** invoke pack callbacks.

    Idempotency is intentionally unsupported in v1 (each POST creates a fresh run).
    """

    sem = getattr(services, "asset_pack_semaphore", None)
    pool = getattr(services, "pool", None)
    if pool is None:
        logger.error(
            "run_single_slot_in_background aborted: DB pool unavailable (run_id=%s)",
            new_run_id,
        )
        return
    if sem is None:
        sem = asyncio.Semaphore(services.settings.max_concurrent_packs)

    slot_eff = slot_with_prompt_modifier_overlay(slot, prompt_modifier_text)
    acquired = False
    await sem.acquire()
    acquired = True
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT site_id FROM external_media_assets WHERE id = $1",
                old_asset_id,
            )
        if row is None:
            logger.error(
                "run_single_slot_in_background: old asset missing old_asset_id=%s",
                old_asset_id,
            )
            await update_run_status(
                pool,
                new_run_id,
                status="failed",
                error="old_asset_missing",
                finished=True,
            )
            return

        site_id = row["site_id"]
        pname = resolve_provider_for_slot(payload, slot_eff)
        provider = _get_image_provider(services, pname)
        palette_hex = _style_palette_hex(style_profile)
        sp = build_slot_prompt(style_profile, slot_eff)
        dims = (slot_eff.layout.dimensions.w, slot_eff.layout.dimensions.h)

        if pending_asset_id is None:
            pending_meta = {
                "slot_id": slot_eff.slot_id,
                "slot_intent": slot_eff.intent,
                "style_profile_id": str(style_profile.id),
                "prompt_hash": sp.prompt_hash,
                "seed": int(seed),
                "determinism_level": "best-effort",
                "run_id": str(new_run_id),
            }
            asset_id = await insert_pending_asset(
                pool,
                agent_run_id=new_run_id,
                site_id=site_id,
                provider=pname,
                model_version=getattr(provider, "model_version", "unknown"),
                metadata=pending_meta,
            )
        else:
            asset_id = pending_asset_id

        async def attempt(call_seed: int | None) -> ProviderResult:
            return await _call_generate_single(
                provider,
                slot_id=slot_eff.slot_id,
                prompt=sp.text,
                dimensions=dims,
                seed=call_seed,
                style_profile=style_profile,
                reference_images=None,
            )

        try:
            pr = await with_retry(
                attempt,
                max_retries=1,
                base_seed=int(seed),
            )
        except RetryExhausted as rex:
            err = str(rex.__cause__ or rex)
            await mark_asset_failed(pool, asset_id, error=err)
            tm = trim_tool_result({"error": err})
            await insert_tool_call(
                pool,
                run_id=new_run_id,
                tool_name="image_generation",
                args={
                    "slot_id": slot_eff.slot_id,
                    "prompt_template_version": sp.prompt_template_version,
                },
                result=tm,
                status="error",
                latency_ms=0,
                cost_cents=0,
                provider=pname,
                model_version=getattr(provider, "model_version", "unknown"),
            )
            await update_run_status(pool, new_run_id, status="failed", error=err, finished=True)
            return

        await _finalize_slot_success(
            pool,
            services,
            run_id=new_run_id,
            payload=payload,
            style_profile=style_profile,
            slot=slot_eff,
            asset_id=asset_id,
            pr=pr,
            palette_hex=palette_hex,
            site_id=site_id,
        )
        await supersede_asset(pool, old_asset_id=old_asset_id, new_asset_id=asset_id)
        await roll_up_cost(pool, new_run_id)
        await update_run_status(pool, new_run_id, status="ok", finished=True)

    except BaseException as exc:
        logger.exception("run_single_slot_in_background failed run_id=%s", new_run_id)
        try:
            await update_run_status(
                pool,
                new_run_id,
                status="failed",
                error=str(exc),
                finished=True,
            )
        except Exception:
            logger.exception(
                "unable to persist failed agent_run status for regenerate run_id=%s",
                new_run_id,
            )

    finally:
        if acquired:
            sem.release()
