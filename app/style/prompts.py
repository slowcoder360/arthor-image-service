"""Deterministic per-slot prompt text from StyleProfile (ADR-0009 §4)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from app.payload.models import Slot
from app.style.profile import StyleProfile

PROMPT_TEMPLATE_VERSION: Literal["1.0"] = "1.0"


@dataclass(frozen=True)
class SlotPrompt:
    text: str
    prompt_hash: str
    prompt_template_version: str


def _hero_overlay_composition(slot: Slot) -> str:
    """Copy-aware composition for homepage hero background plates (no rendered text)."""
    headline = (slot.copy_context.page_h1 or "").strip()
    subhead = (slot.copy_context.section_heading or "").strip()
    inset = slot.layout.safe_area.inset_pct
    mode = slot.layout.safe_area.mode

    if mode == "start":
        zone = (
            f"Keep the left {inset}% of the frame visually quiet: smooth tonal gradient, "
            "soft bokeh, or minimal detail so dark or light headline copy stays legible"
        )
    elif mode == "end":
        zone = f"Keep the right {inset}% visually quiet for overlay copy"
    elif mode == "center":
        zone = f"Keep the center {inset}% visually quiet for overlay copy"
    else:
        zone = f"Keep a {inset}% inset margin uncluttered on all edges"

    copy_lines = [
        "Homepage hero background plate only — no text, typography, logos, buttons, or UI chrome in the image.",
        "Reserve the top 14% as a calm, lower-detail band for site header and navigation overlay.",
        zone + ".",
        "Place the primary subject opposite the copy-safe zone; avoid busy texture behind where headline and CTA will sit.",
    ]
    if headline or subhead:
        planned = f"Planned overlay copy (DO NOT render as text): headline «{headline}»"
        if subhead:
            planned += f"; subhead «{subhead}»"
        planned += ". Use this only to choose subject placement and negative space — never paint the words."
        copy_lines.append(planned)
    return "\n".join(copy_lines)


def build_slot_prompt(profile: StyleProfile, slot: Slot) -> SlotPrompt:
    section_heading = slot.copy_context.section_heading or ""
    comp_join = ", ".join(profile.composition)
    mood_join = ", ".join(profile.mood)
    must_join = ", ".join(profile.must_include)
    avoid_join = ", ".join(profile.do_not)
    w = slot.layout.dimensions.w
    h = slot.layout.dimensions.h
    mode = slot.layout.safe_area.mode
    inset = slot.layout.safe_area.inset_pct

    if slot.slot_kind == "hero" and slot.layout.overlay_text_risk:
        scene_line = f"{slot.subject.primary}. {slot.subject.setting}."
        lines = [
            scene_line,
            _hero_overlay_composition(slot),
            f"Photographic register: {profile.register}. {profile.camera_language}.",
            f"Lighting: {profile.lighting}. {comp_join}. {profile.color_grading}.",
            f"Mood: {mood_join}. {must_join}.",
            f"Avoid: {avoid_join}, rendered words, signage text, watermarks.",
            f"Aspect: {w}x{h}, desktop hero safe area: {mode} inset {inset}%.",
        ]
    else:
        lines = [
            f"{slot.subject.primary}, {slot.subject.setting}, {section_heading}.",
            f"Photographic register: {profile.register}. {profile.camera_language}.",
            f"Lighting: {profile.lighting}. {comp_join}. {profile.color_grading}.",
            f"Mood: {mood_join}. {must_join}.",
            f"Avoid: {avoid_join}.",
            f"Aspect: {w}x{h}, safe area: {mode} inset {inset}%.",
        ]

    text = "\n".join(lines)

    digest = hashlib.sha256(text.encode()).hexdigest()
    return SlotPrompt(
        text=text,
        prompt_hash=digest,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
    )
