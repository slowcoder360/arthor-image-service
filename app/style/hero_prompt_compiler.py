"""Deterministic hero prompt compiler — visual strategy scene brief + brand signals."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.payload.hero_models import HeroCandidatesRequest, HeroVariantSlot, variant_to_slot
from app.payload.models import PaletteTone
from app.style.hero_archetypes import (
    GLOBAL_HERO_AVOID,
    TONE_COMPOSITION,
    format_locale,
    resolve_hero_job,
    resolve_industry,
)
from app.style.hero_visual_strategy import (
    SceneArchetypeId,
    catalog_entry,
    industry_backdrop_modifier,
    resolve_variant_visual_strategy,
)
from app.style.profile import StyleProfile
from app.style.hero_viewports import (
    MOBILE,
    MOBILE_COPY_HINTS,
    MOBILE_TONE_COMPOSITION,
    HeroViewport,
    viewport_spec,
)
from app.style.prompts import PROMPT_TEMPLATE_VERSION, build_slot_prompt

COMPILER_VERSION = "3.0"


def _stack_palette(palette: PaletteTone) -> str:
    return (
        f"Brand palette direction: primary accent {palette.primary}, "
        f"secondary warmth {palette.secondary}, ambient backgrounds near {palette.background}, "
        f"overlay-safe contrast against {palette.foreground}. "
        "Echo primary/secondary in subtle props, upholstery, or light accents — not flat color fills."
    )


def _stack_feel(
    archetype: Any,
    style_profile: StyleProfile,
    brand_tone: str,
) -> str:
    mood = ", ".join(style_profile.mood[:4]) if style_profile.mood else brand_tone
    parts = [archetype.feel]
    if mood.strip():
        parts.append(mood.strip())
    if style_profile.color_grading.strip():
        parts.append(style_profile.color_grading.strip())
    return "Mood and feel: " + "; ".join(parts) + "."


def _stack_lighting_camera(style_profile: StyleProfile) -> str:
    return (
        f"Photographic register: {style_profile.register}. "
        f"{style_profile.camera_language}. "
        f"Lighting: {style_profile.lighting}. "
        f"Composition: {', '.join(style_profile.composition[:5])}."
    )


def _overlay_geometry(
    tone_angle: str | None,
    inset_pct: int,
    w: int,
    h: int,
    *,
    has_cta: bool = False,
    viewport: HeroViewport = "desktop",
) -> list[str]:
    lines = [
        "Homepage hero background plate only — never render text, typography, logos, buttons, menus, or UI.",
    ]
    tone_key = tone_angle or "search"
    if viewport == MOBILE:
        lines.append(
            "Portrait mobile header plate — stacked marketing copy will sit above this image in the page layout."
        )
        comp = MOBILE_TONE_COMPOSITION.get(
            tone_key,
            "subject in lower half; upper portion softer for copy stack — full vertical scene",
        )
        lines.append(comp + ".")
        lines.append(
            f"Copy-safe zone: upper ~{inset_pct}% slightly softer contrast for headline overlay "
            f"({w}x{h} mobile hero) — environmental detail may continue; do not leave a blank void."
        )
        if tone_angle == "offer":
            lines.append(
                "Offer tone: keep upper quiet zone uncluttered for stacked offer copy and CTA — "
                "subject stays in the lower half."
            )
        copy_hint = MOBILE_COPY_HINTS.get(tone_key, "marketing copy stacks in the upper quiet zone")
        lines.append(f"Layout intent ({tone_key}, mobile): {copy_hint}; do not paint any words.")
        return lines

    lines.append(
        (
            "Top 14%: soft ceiling, sky, or gentle gradient band — "
            "never navigation bars, tabs, icons, or interface chrome."
        )
    )
    comp = TONE_COMPOSITION.get(
        tone_key,
        "human subject right-weighted with softer left contrast — full scene, not empty left half",
    )
    lines.append(comp + ".")
    lines.append(
        f"Copy-safe zone: left ~{inset_pct}% slightly softer contrast for headline overlay "
        f"({w}x{h} desktop hero) — environmental detail may continue; do not leave a blank void."
    )
    if tone_angle == "offer":
        cta_note = (
            "Offer tone: keep lower-left quadrant lower-contrast and uncluttered for CTA button overlay"
            if has_cta
            else "Offer tone: additionally keep lower-left quadrant lower-contrast for CTA button overlay"
        )
        lines.append(cta_note + ".")
    copy_hint = {
        "search": "search-intent copy will sit in the left safe zone",
        "story": "trust-building copy will sit in the left safe zone",
        "offer": "offer headline, subhead, and CTA will sit left and lower-left",
    }.get(tone_key, "marketing copy will overlay the quiet zone")
    lines.append(f"Layout intent ({tone_key}, desktop): {copy_hint}; do not paint any words.")
    return lines


def _stack_avoid(
    style_profile: StyleProfile,
    industry_ctx: Any,
    scene_avoid: tuple[str, ...],
) -> str:
    items: list[str] = []
    seen: set[str] = set()
    for src in (
        list(GLOBAL_HERO_AVOID),
        list(scene_avoid),
        list(style_profile.do_not),
        list(industry_ctx.avoid_extra),
    ):
        for item in src:
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                items.append(item.strip())
    extras = (
        "rendered words",
        "signage text",
        "website mockups",
        "browser chrome",
        "app UI",
        "menu bars",
        "watermarks",
    )
    for e in extras:
        if e not in seen:
            items.append(e)
    return "Avoid: " + ", ".join(items[:18]) + "."


def compile_variant_prompt(
    request: HeroCandidatesRequest,
    variant: HeroVariantSlot,
    index: int,
    style_profile: StyleProfile,
    *,
    scene_archetype_override: SceneArchetypeId | None = None,
    prompt_modifier: str | None = None,
) -> str:
    """Deterministic provider prompt for one hero variant."""
    slot = variant_to_slot(request, variant, index)
    ctx = resolve_industry(request.business.industry)
    strategy = resolve_variant_visual_strategy(request, variant, index)
    archetype_id = scene_archetype_override or strategy.scene_archetype
    scene = catalog_entry(archetype_id)
    backdrop = industry_backdrop_modifier(ctx.label)
    locale = format_locale(
        city=request.location.city,
        region=request.location.region,
        country=request.location.country,
    )
    inset = slot.layout.safe_area.inset_pct
    w, h = slot.layout.dimensions.w, slot.layout.dimensions.h
    tone = variant.tone_angle
    has_cta = bool(variant.copy_metrics and variant.copy_metrics.has_cta)
    vp = viewport_spec(request.hero_viewport)

    services_line = ""
    if request.business.priority_services:
        svc = ", ".join(request.business.priority_services[:3])
        services_line = f"Priority services backdrop hint: {svc} — not the hero subject."

    lines = [
        (
            f"Scene archetype: {scene.id}. {scene.subject}. "
            f"Viewport: {vp.label} ({vp.width}x{vp.height}). "
            f"Industry backdrop (modifier only): {backdrop}. "
            f"Business: {request.business.site_name} ({ctx.label}, {locale}). "
            "Show human outcome and connection — never business equipment or empty rooms as hero."
        ),
        f"People: {scene.people}.",
        *_overlay_geometry(
            tone, inset, w, h, has_cta=has_cta, viewport=request.hero_viewport
        ),
        _stack_palette(request.brand_visual.palette.light),
        _stack_feel(ctx, style_profile, request.brand_voice.tone),
        _stack_lighting_camera(style_profile),
    ]
    if services_line:
        lines.append(services_line.strip())
    if style_profile.must_include:
        lines.append("Must include: " + ", ".join(style_profile.must_include[:6]) + ".")
    lines.append(_stack_avoid(style_profile, ctx, scene.avoid))
    prompt = "\n".join(lines)
    if prompt_modifier:
        adj = str(prompt_modifier).strip()
        if adj:
            prompt = f"{prompt} — Adjust: {adj}"
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
) -> list[CompiledHeroPrompt]:
    """Compile all three hero prompts deterministically."""
    out: list[CompiledHeroPrompt] = []
    ctx = resolve_industry(request.business.industry)
    for index, variant in enumerate(request.variants):
        slot = variant_to_slot(request, variant, index)
        seed = build_slot_prompt(style_profile, slot)
        prompt = compile_variant_prompt(request, variant, index, style_profile)
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
