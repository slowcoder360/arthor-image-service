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

    text = "\n".join(
        [
            f"{slot.subject.primary}, {slot.subject.setting}, {section_heading}.",
            f"Photographic register: {profile.register}. {profile.camera_language}.",
            f"Lighting: {profile.lighting}. {comp_join}. {profile.color_grading}.",
            f"Mood: {mood_join}. {must_join}.",
            f"Avoid: {avoid_join}.",
            f"Aspect: {w}x{h}, safe area: {mode} inset {inset}%.",
        ]
    )

    digest = hashlib.sha256(text.encode()).hexdigest()
    return SlotPrompt(
        text=text,
        prompt_hash=digest,
        prompt_template_version=PROMPT_TEMPLATE_VERSION,
    )
