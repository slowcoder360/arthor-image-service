"""Serialize hero compile output into gpt-image-2–native prompts (plain English, line-broken).

OpenAI guidance: subject-first creative brief, photorealistic register, positive composition
constraints, invariants (not long Avoid lists). Format-neutral — no XML/JSON wrappers.
Ref: https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
"""

from __future__ import annotations

from dataclasses import dataclass

SERIALIZER_VERSION = "1.0"


@dataclass(frozen=True)
class HeroPromptBrief:
    """Structured compile output before provider serialization."""

    brand_context: str
    subject: str
    people: str
    setting: str
    composition: str
    photography: str
    mood_and_color: str
    must_include: tuple[str, ...]
    invariants: tuple[str, ...]


def serialize_openai_hero_prompt(brief: HeroPromptBrief) -> str:
    """Model-native prompt string for OpenAI Images generate/edit."""
    parts: list[str] = [
        f"Create a photorealistic homepage hero background plate for {brief.brand_context}.",
        f"Subject: {brief.subject}. {brief.people}",
    ]
    if brief.setting.strip():
        parts.append(f"Setting: {brief.setting.strip()}")
    parts.append(f"Composition: {brief.composition}")
    parts.append(f"Photography: {brief.photography}")
    parts.append(f"Mood and color: {brief.mood_and_color}")
    if brief.must_include:
        parts.append("Include: " + ", ".join(brief.must_include) + ".")
    inv = " ".join(brief.invariants)
    parts.append(f"Invariants: {inv}")
    return "\n\n".join(parts)


def composition_block(
    *,
    tone_angle: str | None,
    inset_pct: int,
    is_mobile: bool,
    has_cta: bool,
) -> str:
    """Positive, placement-first composition language (overlay copy stays in HTML)."""
    tone = tone_angle or "search"
    if is_mobile:
        offer_extra = (
            " Keep the upper quiet zone uncluttered for stacked offer copy and CTA button."
            if tone == "offer"
            else ""
        )
        return (
            f"Portrait photograph. Primary subject anchored in the lower half with candid energy. "
            f"Upper {inset_pct}% kept visually quiet — soft contrast and smooth tonal gradient "
            f"for stacked headline copy.{offer_extra} "
            "Environmental detail continues through the frame — no blank void."
        )

    tone_subject = {
        "search": "Primary human connection placed in the center-right third.",
        "story": "Human connection anchored in the right half with warmth across the frame.",
        "offer": "Outcome or relief moment anchored in the lower-right.",
    }.get(tone, "Primary subject placed in the right two-thirds.")

    cta_zone = (
        " Lower-left quadrant kept smooth and lower-contrast for CTA button overlay."
        if tone == "offer"
        else ""
    )
    if tone == "offer" and not has_cta:
        cta_zone = " Lower-left quadrant kept smooth for optional CTA overlay."

    return (
        f"Wide landscape photograph. {tone_subject} "
        f"Keep the left {inset_pct}% visually quiet — soft bokeh, smooth tonal gradient, "
        "minimal detail so headline copy stays legible. "
        "Calm upper band with lower detail for site header overlay."
        f"{cta_zone} "
        "Environmental detail continues across the full width — balanced scene, not an empty left half."
    )


def photography_block(style_register: str, camera: str, lighting: str, composition_rules: tuple[str, ...]) -> str:
    register = style_register.strip() or "photographic"
    photo_register = register if "photo" in register.lower() else f"photorealistic {register}"
    comp = ", ".join(composition_rules[:4]) if composition_rules else "rule-of-thirds, mid-distance framing"
    return (
        f"{photo_register.capitalize()} quality. {camera.strip()}. "
        f"Lighting: {lighting.strip()}. {comp}. "
        "Candid, unposed energy; honest skin and material texture; no heavy retouching or glamorization."
    )


def collect_invariants(
    *,
    industry_label: str,
    scene_avoid: tuple[str, ...],
    style_do_not: tuple[str, ...],
    industry_avoid_extra: tuple[str, ...],
) -> tuple[str, ...]:
    """Hard exclusions + industry guardrails — short, invariant-style (not a long Avoid list)."""
    core = (
        "Background plate only — HTML will overlay headline and CTA; do not render typography, "
        "logos, buttons, watermarks, menus, or UI chrome in the image.",
    )
    industry_guards: dict[str, str] = {
        "dental": (
            "Recognizable dental clinic environment only — exclude residential home, living room, "
            "or kitchen interiors; exclude operatory, dental chair, and instrument close-ups as focal subjects."
        ),
        "healthcare": (
            "Recognizable medical clinic environment — exclude residential interiors and "
            "treatment-room equipment as hero subjects."
        ),
    }
    guards: list[str] = [core[0]]
    if industry_label in industry_guards:
        guards.append(industry_guards[industry_label])

    critical: list[str] = []
    seen: set[str] = set()
    for item in (*scene_avoid, *industry_avoid_extra, *style_do_not):
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if any(
            token in key
            for token in (
                "rendered",
                "operatory",
                "dental chair",
                "residential",
                "living room",
                "equipment",
                "stock",
                "signage",
            )
        ):
            critical.append(item.strip())
        if len(critical) >= 6:
            break

    if critical:
        guards.append("Also exclude: " + "; ".join(critical) + ".")
    return tuple(guards)
