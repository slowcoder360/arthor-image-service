"""Deterministic hero prompt compiler — visual strategy scene brief + brand signals."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.payload.hero_models import HeroCandidatesRequest, HeroVariantSlot, variant_to_slot
from app.style.hero_archetypes import (
    format_locale,
    resolve_hero_job,
    resolve_industry,
)
from app.style.hero_visual_strategy import (
    SceneArchetypeId,
    catalog_entry,
    hero_subject_guidance,
    industry_backdrop_modifier,
    industry_environment_anchors,
    resolve_variant_visual_strategy,
)
from app.style.profile import StyleProfile
from app.style.hero_viewports import MOBILE, viewport_spec
from app.style.hero_openai_prompt_serializer import (
    HeroPromptBrief,
    collect_invariants,
    composition_block,
    photography_block,
    serialize_openai_hero_prompt,
)
from app.style.prompts import build_slot_prompt

COMPILER_VERSION = "3.3"


def build_hero_prompt_brief(
    request: HeroCandidatesRequest,
    variant: HeroVariantSlot,
    index: int,
    style_profile: StyleProfile,
    *,
    scene_archetype_override: SceneArchetypeId | None = None,
) -> HeroPromptBrief:
    ctx = resolve_industry(request.business.industry)
    archetype_id = scene_archetype_override or resolve_variant_visual_strategy(
        request, variant, index
    ).scene_archetype
    scene = catalog_entry(archetype_id)
    backdrop = industry_backdrop_modifier(ctx.label)
    locale = format_locale(
        city=request.location.city,
        region=request.location.region,
        country=request.location.country,
    )
    slot = variant_to_slot(request, variant, index)
    inset = slot.layout.safe_area.inset_pct
    tone = variant.tone_angle
    has_cta = bool(variant.copy_metrics and variant.copy_metrics.has_cta)
    vp = viewport_spec(request.hero_viewport)
    env_anchors = industry_environment_anchors(ctx.label)

    setting_parts = [backdrop, hero_subject_guidance(ctx.label)]
    if env_anchors:
        setting_parts.append(env_anchors)
    if request.business.priority_services:
        svc = ", ".join(request.business.priority_services[:3])
        setting_parts.append(f"Priority services as subtle backdrop context only: {svc}.")

    palette = request.brand_visual.palette.light
    mood = ", ".join(style_profile.mood[:4]) if style_profile.mood else request.brand_voice.tone
    mood_bits = [ctx.feel, mood.strip()]
    if style_profile.color_grading.strip():
        mood_bits.append(style_profile.color_grading.strip())
    mood_bits.append(
        f"primary accent {palette.primary}, secondary {palette.secondary}, "
        f"ambient backgrounds near {palette.background}"
    )

    return HeroPromptBrief(
        brand_context=f"{request.business.site_name} ({ctx.label}, {locale})",
        subject=scene.subject,
        people=scene.people,
        setting=". ".join(p.strip().rstrip(".") for p in setting_parts if p) + ".",
        composition=composition_block(
            tone_angle=tone,
            inset_pct=inset,
            is_mobile=vp.viewport == MOBILE,
            has_cta=has_cta,
        ),
        photography=photography_block(
            style_profile.register,
            style_profile.camera_language,
            style_profile.lighting,
            tuple(style_profile.composition),
        ),
        mood_and_color="; ".join(p for p in mood_bits if p) + ".",
        must_include=tuple(style_profile.must_include[:6]),
        invariants=collect_invariants(
            industry_label=ctx.label,
            scene_avoid=scene.avoid,
            style_do_not=tuple(style_profile.do_not),
            industry_avoid_extra=ctx.avoid_extra,
        ),
    )


def compile_variant_prompt(
    request: HeroCandidatesRequest,
    variant: HeroVariantSlot,
    index: int,
    style_profile: StyleProfile,
    *,
    scene_archetype_override: SceneArchetypeId | None = None,
    prompt_modifier: str | None = None,
    desktop_seed_edit: bool = False,
) -> str:
    """Deterministic gpt-image-2 provider prompt for one hero variant."""
    brief = build_hero_prompt_brief(
        request,
        variant,
        index,
        style_profile,
        scene_archetype_override=scene_archetype_override,
    )
    prompt = serialize_openai_hero_prompt(brief)
    if desktop_seed_edit:
        from app.style.hero_desktop_seed import DESKTOP_SEED_EDIT_MODIFIER

        prompt = f"{prompt}\n\nAdjust: {DESKTOP_SEED_EDIT_MODIFIER}"
    if prompt_modifier:
        adj = str(prompt_modifier).strip()
        if adj:
            prompt = f"{prompt}\n\nAdjust: {adj}"
    return prompt


def prompt_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class CompiledHeroPrompt:
    variant_index: int
    tone_angle: str | None
    prompt: str
    prompt_hash: str
    seed_prompt_hash: str
    compiler_version: str
    industry_label: str
    hero_job: str
    hero_viewport: str
    scene_archetype: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_index": self.variant_index,
            "tone_angle": self.tone_angle,
            "hero_job": self.hero_job,
            "hero_viewport": self.hero_viewport,
            "scene_archetype": self.scene_archetype,
            "prompt": self.prompt,
            "prompt_hash": self.prompt_hash,
            "seed_prompt_hash": self.seed_prompt_hash,
            "compiler_version": self.compiler_version,
            "industry_label": self.industry_label,
        }


def compile_hero_triad_prompts(
    request: HeroCandidatesRequest,
    style_profile: StyleProfile,
    *,
    desktop_seed_edit: bool = False,
) -> list[CompiledHeroPrompt]:
    """Compile all three hero prompts deterministically."""
    out: list[CompiledHeroPrompt] = []
    ctx = resolve_industry(request.business.industry)
    for index, variant in enumerate(request.variants):
        slot = variant_to_slot(request, variant, index)
        seed = build_slot_prompt(style_profile, slot)
        prompt = compile_variant_prompt(
            request,
            variant,
            index,
            style_profile,
            desktop_seed_edit=desktop_seed_edit,
        )
        vstrategy = resolve_variant_visual_strategy(request, variant, index)
        out.append(
            CompiledHeroPrompt(
                variant_index=index,
                tone_angle=variant.tone_angle,
                prompt=prompt,
                prompt_hash=prompt_text_hash(prompt),
                seed_prompt_hash=seed.prompt_hash,
                compiler_version=COMPILER_VERSION,
                industry_label=ctx.label,
                hero_job=resolve_hero_job(variant.tone_angle),
                hero_viewport=request.hero_viewport,
                scene_archetype=vstrategy.scene_archetype,
            )
        )
    return out
