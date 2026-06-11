"""LLM prompt-improvement loop for hero slots (seed prompt → provider-ready text)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import openai

from app.config import Settings
from app.payload.hero_models import HeroCandidatesRequest, HeroVariantSlot, variant_to_slot
from app.payload.models import Slot
from app.style.hero_prompt_compiler import CompiledHeroPrompt, compile_hero_triad_prompts, prompt_text_hash
from app.style.profile import StyleProfile
from app.style.hero_archetypes import resolve_hero_job
from app.style.prompts import SlotPrompt

logger = logging.getLogger(__name__)

PROMPT_IMPROVER_VERSION = "1.0"

_SYSTEM = """You rewrite image-generation prompts for homepage hero background plates.
You receive JSON with business context, brand palette, overlay layout, copy metrics, and a seed prompt.
Reply with ONLY the final prompt text — no markdown, no JSON, no explanation.

Hard rules:
- Never instruct rendering text, typography, logos, buttons, menus, tabs, icons, or UI chrome
- Headline/subhead in input are for spatial planning only — size negative space, never quote or paint them
- Hero job first: show human trust, outcome, experience, or authority — not empty equipment or rooms
- Industry sets backdrop only; avoid chair/operatory/conference-table/equipment as hero subject
- Left copy zone: softer contrast, not a blank void — keep scene continuity across the frame
- Respect people_policy, tone_angle intent, hero_job, and do_not lists
- Incorporate palette hex as color-grading direction, not swatches of flat color
- Photographic register unless input says otherwise
- Stay under 1200 characters"""


@dataclass(frozen=True)
class PromptImproveResult:
    text: str
    improved: bool
    model: str | None = None
    used_fallback: bool = False


class PromptImprover(Protocol):
    async def improve(self, brief: dict[str, Any], seed_prompt: str) -> PromptImproveResult:
        ...


def prompt_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def build_hero_improve_brief(
    request: HeroCandidatesRequest,
    variant: HeroVariantSlot,
    slot: Slot,
    style_profile: StyleProfile,
) -> dict[str, Any]:
    """Structured brief for the improver — not the raw provider prompt."""
    palette = request.brand_visual.palette.light
    return {
        "prompt_improver_version": PROMPT_IMPROVER_VERSION,
        "business": {
            "site_name": request.business.site_name,
            "industry": request.business.industry,
            "value_prop": request.business.value_prop,
            "icp_summary": request.business.icp_summary,
            "priority_services": list(request.business.priority_services),
            "forbidden_subjects": list(request.business.forbidden_subjects),
        },
        "location": request.location.model_dump(mode="json"),
        "brand_voice": {
            "tone": request.brand_voice.tone,
            "style_direction": request.brand_voice.style_direction,
            "do_not": list(request.brand_voice.do_not),
        },
        "variant": {
            "tone_angle": variant.tone_angle,
            "hero_job": resolve_hero_job(variant.tone_angle),
            "intent": slot.intent,
            "copy": {
                "headline": variant.headline,
                "subhead": variant.subhead,
                "headline_chars": (
                    variant.copy_metrics.headline_chars
                    if variant.copy_metrics
                    else len(variant.headline or "")
                ),
                "has_subhead": (
                    variant.copy_metrics.has_subhead
                    if variant.copy_metrics
                    else bool(variant.subhead and variant.subhead.strip())
                ),
                "has_cta": variant.copy_metrics.has_cta if variant.copy_metrics else False,
                "cta_chars": variant.copy_metrics.cta_chars if variant.copy_metrics else 0,
                "nav_count": variant.copy_metrics.nav_count if variant.copy_metrics else 0,
            },
        },
        "overlay_layout": {
            "safe_area_mode": slot.layout.safe_area.mode,
            "inset_pct": slot.layout.safe_area.inset_pct,
            "dimensions": {
                "w": slot.layout.dimensions.w,
                "h": slot.layout.dimensions.h,
            },
            "overlay_text_risk": slot.layout.overlay_text_risk,
        },
        "subject": {
            "primary": slot.subject.primary,
            "setting": slot.subject.setting,
            "people_policy": slot.subject.people_policy.model_dump(mode="json"),
        },
        "style": {
            "register": style_profile.register,
            "lighting": style_profile.lighting,
            "camera_language": style_profile.camera_language,
            "color_grading": style_profile.color_grading,
            "mood": list(style_profile.mood),
            "composition": list(style_profile.composition),
            "do_not": list(style_profile.do_not),
            "must_include": list(style_profile.must_include),
        },
        "palette": {
            "primary": palette.primary,
            "secondary": palette.secondary,
            "background": palette.background,
            "foreground": palette.foreground,
        },
    }


class OpenAIPromptImprover:
    """Chat-completions rewriter; falls back to seed prompt on failure."""

    def __init__(self, settings: Settings) -> None:
        api_key = settings.openai_api_key or "unset-openai-key"
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = settings.hero_prompt_improve_model
        self._timeout = settings.hero_prompt_improve_timeout_seconds

    async def improve(self, brief: dict[str, Any], seed_prompt: str) -> PromptImproveResult:
        user_payload = {**brief, "seed_prompt": seed_prompt}
        try:
            resp = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                    ],
                    temperature=0.35,
                    max_tokens=900,
                ),
                timeout=self._timeout,
            )
        except (TimeoutError, asyncio.TimeoutError, openai.APIError, Exception) as exc:
            logger.warning("hero prompt improver failed, using seed prompt: %s", exc)
            return PromptImproveResult(
                text=seed_prompt,
                improved=False,
                model=self._model,
                used_fallback=True,
            )

        choice = resp.choices[0].message.content if resp.choices else None
        text = (choice or "").strip()
        if not text:
            return PromptImproveResult(
                text=seed_prompt,
                improved=False,
                model=self._model,
                used_fallback=True,
            )
        return PromptImproveResult(text=text, improved=True, model=self._model, used_fallback=False)


async def resolve_hero_provider_prompt(
    services: Any,
    *,
    request: HeroCandidatesRequest,
    variant: HeroVariantSlot,
    slot: Slot,
    style_profile: StyleProfile,
    seed_prompt: SlotPrompt,
) -> tuple[str, str, dict[str, Any]]:
    """Return (provider_prompt, prompt_hash, metadata_patch)."""
    settings: Settings = services.settings
    meta: dict[str, Any] = {
        "prompt_improved": False,
        "base_prompt_hash": seed_prompt.prompt_hash,
        "prompt_template_version": seed_prompt.prompt_template_version,
    }
    text = seed_prompt.text
    if not settings.hero_prompt_improve_enabled:
        return text, seed_prompt.prompt_hash, meta

    improver: PromptImprover | None = getattr(services, "prompt_improver", None)
    if improver is None:
        return text, seed_prompt.prompt_hash, meta

    brief = build_hero_improve_brief(request, variant, slot, style_profile)
    result = await improver.improve(brief, seed_prompt.text)
    text = result.text
    meta["prompt_improved"] = result.improved
    meta["prompt_improver_model"] = result.model
    meta["prompt_improver_fallback"] = result.used_fallback
    if result.improved:
        meta["improved_prompt_hash"] = prompt_text_hash(text)
        return text, meta["improved_prompt_hash"], meta
    return text, seed_prompt.prompt_hash, meta


def build_prompt_improver(settings: Settings) -> PromptImprover | None:
    if not settings.hero_prompt_improve_enabled:
        return None
    if not settings.openai_api_key:
        return None
    return OpenAIPromptImprover(settings)


def _improver_applies(idempotency_key: str, canary_pct: float) -> bool:
    if canary_pct <= 0:
        return False
    if canary_pct >= 100:
        return True
    bucket = int(hashlib.sha256(idempotency_key.encode()).hexdigest()[:8], 16) % 100
    return bucket < canary_pct


async def finalize_hero_triad_prompts(
    services: Any,
    request: HeroCandidatesRequest,
    style_profile: StyleProfile,
) -> list[CompiledHeroPrompt]:
    """Deterministic compile, then optional LLM pass (parallel, canary-gated)."""
    compiled = compile_hero_triad_prompts(request, style_profile)
    settings: Settings = services.settings
    if not settings.hero_prompt_improve_enabled:
        services._last_hero_improver_stats = None
        return compiled
    if not _improver_applies(request.idempotency_key, settings.hero_prompt_improve_canary_pct):
        services._last_hero_improver_stats = {
            "canary_applied": False,
            "improved_count": 0,
            "fallback_count": 0,
        }
        return compiled
    improver: PromptImprover | None = getattr(services, "prompt_improver", None)
    if improver is None:
        services._last_hero_improver_stats = None
        return compiled

    improved_count = 0
    fallback_count = 0

    async def _one(entry: CompiledHeroPrompt) -> CompiledHeroPrompt:
        nonlocal improved_count, fallback_count
        from dataclasses import replace

        variant = request.variants[entry.variant_index]
        slot = variant_to_slot(request, variant, entry.variant_index)
        brief = build_hero_improve_brief(request, variant, slot, style_profile)
        result = await improver.improve(brief, entry.prompt)
        if result.used_fallback:
            fallback_count += 1
        if not result.improved:
            return entry
        improved_count += 1
        return replace(
            entry,
            prompt=result.text,
            prompt_hash=prompt_text_hash(result.text),
        )

    out = list(await asyncio.gather(*[_one(e) for e in compiled]))
    services._last_hero_improver_stats = {
        "canary_applied": True,
        "improved_count": improved_count,
        "fallback_count": fallback_count,
    }
    return out
