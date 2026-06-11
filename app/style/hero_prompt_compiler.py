"""Deterministic hero prompt compiler — industry templates + stacked brand signals."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.payload.hero_models import HeroCandidatesRequest, HeroVariantSlot, variant_to_slot
from app.payload.models import PaletteTone
from app.style.hero_archetypes import (
    TONE_COMPOSITION,
    TONE_PEOPLE,
    format_locale,
    resolve_industry,
)
from app.style.profile import StyleProfile
from app.style.prompts import PROMPT_TEMPLATE_VERSION, build_slot_prompt

COMPILER_VERSION = "1.0"


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
) -> list[str]:
    lines = [
        "Homepage hero background plate only — never render text, typography, logos, buttons, menus, or UI.",
        (
            f"Top 14%: empty wall, ceiling, or soft gradient band only — "
            "never navigation bars, tabs, icons, or interface chrome."
        ),
    ]
    tone_key = tone_angle or "search"
    comp = TONE_COMPOSITION.get(tone_key, "subject off-center with generous negative space for copy overlay")
    lines.append(comp + ".")
    lines.append(
        f"Global safe area: left inset {inset_pct}% kept low-detail for headline overlay "
        f"({w}x{h} desktop hero)."
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
    lines.append(f"Layout intent ({tone_key}): {copy_hint}; do not paint any words.")
    return lines


def _stack_avoid(style_profile: StyleProfile, archetype: Any) -> str:
    items: list[str] = []
    seen: set[str] = set()
    for src in (list(style_profile.do_not), list(archetype.avoid_extra)):
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
) -> str:
    """Deterministic provider prompt for one hero variant."""
    slot = variant_to_slot(request, variant, index)
    archetype = resolve_industry(request.business.industry)
    locale = format_locale(
        city=request.location.city,
        region=request.location.region,
        country=request.location.country,
    )
    palette = request.brand_visual.palette.light
    inset = slot.layout.safe_area.inset_pct
    w, h = slot.layout.dimensions.w, slot.layout.dimensions.h
    tone = variant.tone_angle
    people = TONE_PEOPLE.get(tone or "search", TONE_PEOPLE["search"])
    has_cta = bool(variant.copy_metrics and variant.copy_metrics.has_cta)

    services_line = ""
    if request.business.priority_services:
        svc = ", ".join(request.business.priority_services[:3])
        services_line = f"Priority services context: {svc}."
    if request.business.value_prop.strip():
        services_line = (services_line + " " if services_line else "") + (
            f"Value context: {request.business.value_prop[:120]}."
        )

    lines = [
        (
            f"{archetype.scene} for {request.business.site_name} ({archetype.label}, {locale}). "
            f"Visual anchors: {', '.join(archetype.anchors)}."
        ),
        f"People: {people}.",
        *_overlay_geometry(tone, inset, w, h, has_cta=has_cta),
        _stack_palette(palette),
        _stack_feel(archetype, style_profile, request.brand_voice.tone),
        _stack_lighting_camera(style_profile),
    ]
    if services_line:
        lines.append(services_line.strip())
    if style_profile.must_include:
        lines.append("Must include: " + ", ".join(style_profile.must_include[:6]) + ".")
    lines.append(_stack_avoid(style_profile, archetype))
    return "\n".join(lines)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_index": self.variant_index,
            "tone_angle": self.tone_angle,
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
    archetype = resolve_industry(request.business.industry)
    for index, variant in enumerate(request.variants):
        slot = variant_to_slot(request, variant, index)
        seed = build_slot_prompt(style_profile, slot)
        prompt = compile_variant_prompt(request, variant, index, style_profile)
        out.append(
            CompiledHeroPrompt(
                variant_index=index,
                tone_angle=variant.tone_angle,
                prompt=prompt,
                prompt_hash=prompt_text_hash(prompt),
                seed_prompt_hash=seed.prompt_hash,
                compiler_version=COMPILER_VERSION,
                industry_label=archetype.label,
            )
        )
    return out
