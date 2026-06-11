"""Deterministic hero visual strategy — scene archetypes and authenticity modes (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.payload.hero_models import HeroCandidatesRequest, HeroVariantSlot
from app.style.hero_archetypes import resolve_industry

SceneArchetypeId = Literal[
    "shared_joy",
    "confident_smile",
    "threshold_invitation",
    "threshold_relief",
    "desk_side_guidance",
    "environment_warmth",
]

AuthenticityMode = Literal["stylized", "space_anchored", "likeness_anchored"]

STRATEGY_VERSION = "1.1"
SCENE_CATALOG_VERSION = "1.1"

_FAMILY_ICP_KEYS: tuple[str, ...] = (
    "famil",
    "parent",
    "child",
    "kid",
    "pediatric",
    "youth",
)

_TONE_DEFAULT_ARCHETYPE: dict[str, SceneArchetypeId] = {
    "search": "confident_smile",
    "story": "threshold_relief",
    "offer": "confident_smile",
}

_FAMILY_DENTAL_TRIAD: dict[str, SceneArchetypeId] = {
    "search": "shared_joy",
    "story": "shared_joy",
    "offer": "confident_smile",
}


@dataclass(frozen=True)
class SceneArchetype:
    """Cross-industry scene template — subject is archetype, not industry equipment."""

    id: SceneArchetypeId
    subject: str
    people: str
    avoid: tuple[str, ...]


SCENE_CATALOG: dict[SceneArchetypeId, SceneArchetype] = {
    "shared_joy": SceneArchetype(
        id="shared_joy",
        subject="candid shared joy — two people in warm eye contact, natural smiles",
        people=(
            "genuine connection between people — parent and child, friends, or partners; "
            "soft profiles acceptable; not stock grin at camera"
        ),
        avoid=(
            "empty operatory or clinical room as hero",
            "equipment as hero subject",
            "posed advertisement smile at lens",
        ),
    ),
    "confident_smile": SceneArchetype(
        id="confident_smile",
        subject="natural adult confident smile — warm light, relaxed posture, approachable energy",
        people="single adult or small group; candid warmth; not direct-to-camera stock portrait",
        avoid=("forced grin at camera", "empty clinical room", "equipment focal point"),
    ),
    "threshold_invitation": SceneArchetype(
        id="threshold_invitation",
        subject="welcoming threshold moment — provider in doorway or entry with open gesture",
        people="provider inviting customer inward; standing, not seated consultation",
        avoid=(
            "seated consultation in chairs",
            "dental chair or operatory",
            "authority-only headshot",
        ),
    ),
    "threshold_relief": SceneArchetype(
        id="threshold_relief",
        subject="relief at the threshold — customer leaving satisfied, relaxed body language",
        people="family or individual exiting with ease; natural movement; not clinical room hero",
        avoid=("clinical treatment room as hero", "equipment visible", "posed relief at camera"),
    ),
    "desk_side_guidance": SceneArchetype(
        id="desk_side_guidance",
        subject="plan conversation at a side table or desk — collaborative guidance, no procedure chairs",
        people="provider and customer engaged in discussion; seated at table, not exam chairs",
        avoid=(
            "dental chair or operatory",
            "seated consultation in matching armchairs as default",
            "authority-only lecturing pose",
        ),
    ),
    "environment_warmth": SceneArchetype(
        id="environment_warmth",
        subject="warm environment portrait — light, materials, kid-friendly details; people optional",
        people="no faces required; human-scale warmth through space, light, and texture",
        avoid=("empty sterile room", "equipment hero", "rendered signage"),
    ),
}

INDUSTRY_BACKDROP_MODIFIERS: dict[str, str] = {
    # DR 20: clinic interior/exterior, warm light, clean-not-scary; no instrument close-ups.
    "dental": (
        "bright modern dental clinic — reception, consult nook, or hallway with subtle practice cues "
        "(clean whites, soft blues, kid-friendly details); soft window light; clearly a dental office"
    ),
    "legal": "measured professional law office warmth — human consultation, not empty conference room",
    "home_services": "well-maintained home interior — comfort and protection, not equipment hero",
    "healthcare": (
        "welcoming medical clinic interior — clean, calm, human-centered; not treatment-room equipment hero"
    ),
    "general_services": "credible local professional service setting with natural light",
}

INDUSTRY_ENVIRONMENT_ANCHORS: dict[str, str] = {
    "dental": (
        "Environment anchors: recognizable dental practice (reception desk, clinic corridor, or consult area "
        "in background); neutral dental décor; shallow depth of field ok; no operatory, dental chair, "
        "or instruments as focal point"
    ),
    "healthcare": (
        "Environment anchors: recognizable clinic or medical office background; clean and reassuring; "
        "no procedure room or clinical hardware as hero"
    ),
}

INDUSTRY_SUBJECT_GUIDANCE: dict[str, str] = {
    "dental": (
        "People are the hero subject; dental clinic environment visible behind them — "
        "never a residential home, living room, or kitchen"
    ),
    "healthcare": (
        "People are the hero subject; healthcare clinic environment visible — not a residential interior"
    ),
}


def _is_family_icp(icp_summary: str) -> bool:
    low = icp_summary.lower()
    return any(k in low for k in _FAMILY_ICP_KEYS)


def resolve_authenticity_mode(request: HeroCandidatesRequest) -> AuthenticityMode:
    refs = request.brand_visual.customer_reference_assets
    if not refs:
        return "stylized"
    roles = {str(getattr(r, "role", "") or "").lower() for r in refs}
    if "team" in roles:
        return "likeness_anchored"
    if "interior" in roles or "ambient" in roles:
        return "space_anchored"
    return "stylized"


def resolve_scene_archetype(
    request: HeroCandidatesRequest,
    variant: HeroVariantSlot,
) -> SceneArchetypeId:
    """Lookup scene archetype from tone, industry, and ICP — deterministic, no LLM."""
    tone = variant.tone_angle or "search"
    ctx = resolve_industry(request.business.industry)
    family = _is_family_icp(request.business.icp_summary)

    if ctx.label == "dental" and family:
        return _FAMILY_DENTAL_TRIAD.get(tone, _TONE_DEFAULT_ARCHETYPE.get(tone, "confident_smile"))

    if tone == "search" and family:
        return "shared_joy"
    if tone == "story" and family:
        return "shared_joy"
    if tone == "offer":
        return "confident_smile"
    if tone == "search":
        return "threshold_invitation" if ctx.label in ("legal", "healthcare") else "confident_smile"
    if tone == "story":
        return "threshold_relief"
    return _TONE_DEFAULT_ARCHETYPE.get(tone, "confident_smile")


def industry_backdrop_modifier(industry_label: str) -> str:
    return INDUSTRY_BACKDROP_MODIFIERS.get(
        industry_label,
        INDUSTRY_BACKDROP_MODIFIERS["general_services"],
    )


def industry_environment_anchors(industry_label: str) -> str | None:
    return INDUSTRY_ENVIRONMENT_ANCHORS.get(industry_label)


def hero_subject_guidance(industry_label: str) -> str:
    return INDUSTRY_SUBJECT_GUIDANCE.get(
        industry_label,
        "Show human outcome and connection — never business equipment or empty rooms as hero.",
    )


def catalog_entry(archetype_id: SceneArchetypeId) -> SceneArchetype:
    return SCENE_CATALOG[archetype_id]


@dataclass(frozen=True)
class VariantVisualStrategy:
    variant_index: int
    tone_angle: str | None
    scene_archetype: SceneArchetypeId
    authenticity_mode: AuthenticityMode

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_index": self.variant_index,
            "tone_angle": self.tone_angle,
            "scene_archetype": self.scene_archetype,
            "authenticity_mode": self.authenticity_mode,
        }


@dataclass(frozen=True)
class HeroVisualStrategy:
    strategy_version: str
    scene_catalog_version: str
    authenticity_mode: AuthenticityMode
    industry_label: str
    variants: tuple[VariantVisualStrategy, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_version": self.strategy_version,
            "scene_catalog_version": self.scene_catalog_version,
            "authenticity_mode": self.authenticity_mode,
            "industry_label": self.industry_label,
            "variants": [v.to_dict() for v in self.variants],
        }


def resolve_hero_visual_strategy(request: HeroCandidatesRequest) -> HeroVisualStrategy:
    """Resolve full triad visual strategy for run metadata and compiler."""
    ctx = resolve_industry(request.business.industry)
    auth = resolve_authenticity_mode(request)
    variants: list[VariantVisualStrategy] = []
    for index, variant in enumerate(request.variants):
        archetype = resolve_scene_archetype(request, variant)
        variants.append(
            VariantVisualStrategy(
                variant_index=index,
                tone_angle=variant.tone_angle,
                scene_archetype=archetype,
                authenticity_mode=auth,
            )
        )
    return HeroVisualStrategy(
        strategy_version=STRATEGY_VERSION,
        scene_catalog_version=SCENE_CATALOG_VERSION,
        authenticity_mode=auth,
        industry_label=ctx.label,
        variants=tuple(variants),
    )


def resolve_variant_visual_strategy(
    request: HeroCandidatesRequest,
    variant: HeroVariantSlot,
    index: int,
) -> VariantVisualStrategy:
    ctx = resolve_industry(request.business.industry)
    return VariantVisualStrategy(
        variant_index=index,
        tone_angle=variant.tone_angle,
        scene_archetype=resolve_scene_archetype(request, variant),
        authenticity_mode=resolve_authenticity_mode(request),
    )
