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

STRATEGY_VERSION = "1.4"
SCENE_CATALOG_VERSION = "1.3"

# Builder visual triad: variant_index 0|1|2 → distinct scene archetypes per industry.
# tone_angle remains on ingress for analytics only — not scene selection.
INDUSTRY_VISUAL_TRIAD: dict[str, tuple[SceneArchetypeId, SceneArchetypeId, SceneArchetypeId]] = {
    "dental": ("threshold_invitation", "shared_joy", "confident_smile"),
    "legal": ("desk_side_guidance", "threshold_invitation", "confident_smile"),
    "home_services": ("threshold_invitation", "desk_side_guidance", "environment_warmth"),
    "healthcare": ("threshold_invitation", "desk_side_guidance", "confident_smile"),
    "outdoor_services": ("environment_warmth", "confident_smile", "threshold_relief"),
    "general_services": ("desk_side_guidance", "threshold_invitation", "confident_smile"),
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
    "legal": "measured professional law office — attorney and client at desk, not family at threshold",
    "home_services": (
        "on-site home service at exterior work area — roofline, garage facade, utility area, or driveway; "
        "homeowner face visible, technician back or profile; not couch leisure"
    ),
    "healthcare": (
        "welcoming clinic or therapy office — provider in scrubs or white coat, patient in street clothes; "
        "not gym, athletic wear, or residential interior"
    ),
    "outdoor_services": (
        "outdoor property with lawn, garden, or yard maintenance visible — daylight, not indoor domestic scenes"
    ),
    "general_services": "professional service consult or on-site visit — not kitchen-table or couch leisure",
}

INDUSTRY_ENVIRONMENT_ANCHORS: dict[str, str] = {
    "dental": (
        "Environment anchors: recognizable dental practice (reception desk, clinic corridor, or consult area "
        "in background); neutral dental décor; shallow depth of field ok; no operatory, dental chair, "
        "or instruments as focal point"
    ),
    "healthcare": (
        "Environment anchors: recognizable clinic or therapy consult room; provider in scrubs or white coat ONLY, "
        "patient in everyday street clothes; no gym equipment, both subjects in medical attire, or residential interior"
    ),
    "legal": (
        "Environment anchors: law office consult room with desk or table; professional attire; "
        "attorney and single client — not a family group at a doorway"
    ),
    "home_services": (
        "Environment anchors: home exterior work site — roofline, garage facade, utility area, or driveway concrete "
        "with technician present; homeowner face toward camera, provider back or profile — not living-room couch "
        "leisure or doorway inversion"
    ),
    "outdoor_services": (
        "Environment anchors: lawn, garden, or landscaped yard; outdoor daylight; "
        "crew or landscaper with homeowner on the property"
    ),
}

INDUSTRY_SUBJECT_GUIDANCE: dict[str, str] = {
    "dental": (
        "People are the hero subject with gender and age diversity (mix of adults and children, male and female); "
        "dental clinic environment visible behind them — never a residential home, living room, or kitchen"
    ),
    "healthcare": (
        "Exactly one person in scrubs, white coat, or clinical uniform; patient in everyday street clothes; "
        "both faces visible at desk consult — never both subjects in medical attire"
    ),
    "legal": (
        "Attorney and client in one-on-one consultation — not a family walking through a doorway"
    ),
    "home_services": (
        "Homeowner face visible toward camera; technician with back, three-quarter rear, or profile at exterior "
        "work site — roofline, garage facade, utility area, or driveway; not passive family on couch, not seated "
        "patio scenes, not provider welcoming homeowner into their own home"
    ),
    "outdoor_services": (
        "Landscaping, tree removal, or fence work outdoors — crew or pro with homeowner on property; "
        "not kitchen-table or living-room leisure"
    ),
    "general_services": (
        "Provider and customer with visible service context — not domestic leisure without a service cue"
    ),
}

# Industry-specific scene people overrides (archetype × label).
INDUSTRY_SCENE_PEOPLE_OVERRIDES: dict[tuple[str, SceneArchetypeId], str] = {
    ("home_services", "threshold_invitation"): (
        "homeowner approaching from outside with face visible toward camera; technician at exterior work site "
        "with back, three-quarter rear, or profile — not provider in doorway welcoming customer inward"
    ),
}

# Vertical keyword overrides within general_services (product/environment hero, not desk consult).
_VERTICAL_SUBJECT_GUIDANCE: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("restaurant", "cafe", "bistro", "dining"),
        "Food and venue as hero — warm dining room, plated dishes, or inviting restaurant interior; "
        "people optional; not desk-side consultation",
    ),
    (
        ("salon", "hair salon", "barber", "spa nail"),
        "Salon chair, mirror station, and styling context as hero — product and environment focus; "
        "not desk-side consultation",
    ),
    (
        ("pool clean", "pool service", "pool maintenance"),
        "Pool and outdoor backyard setting as hero — sparkling water, deck, and maintenance context; "
        "not desk-side consultation",
    ),
)

_PRODUCT_HERO_INDEX_ZERO_KEYS: tuple[str, ...] = (
    "restaurant",
    "cafe",
    "bistro",
    "salon",
    "hair salon",
    "barber",
    "pool clean",
    "pool service",
    "pool maintenance",
)


def resolve_vertical_subject_guidance(industry: str) -> str | None:
    low = industry.lower()
    for keys, guidance in _VERTICAL_SUBJECT_GUIDANCE:
        if any(k in low for k in keys):
            return guidance
    return None


def scene_people_for_industry(archetype_id: SceneArchetypeId, industry_label: str) -> str | None:
    return INDUSTRY_SCENE_PEOPLE_OVERRIDES.get((industry_label, archetype_id))


def _is_product_hero_industry(industry: str) -> bool:
    low = industry.lower()
    return any(k in low for k in _PRODUCT_HERO_INDEX_ZERO_KEYS)


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
    variant_index: int,
) -> SceneArchetypeId:
    """Lookup scene archetype from industry + variant_index — deterministic, no LLM."""
    if variant_index not in (0, 1, 2):
        raise ValueError("variant_index must be 0, 1, or 2")
    industry = request.business.industry
    if variant_index == 0 and _is_product_hero_industry(industry):
        return "environment_warmth"
    ctx = resolve_industry(industry)
    triad = INDUSTRY_VISUAL_TRIAD.get(
        ctx.label,
        INDUSTRY_VISUAL_TRIAD["general_services"],
    )
    return triad[variant_index]


def industry_backdrop_modifier(industry_label: str) -> str:
    return INDUSTRY_BACKDROP_MODIFIERS.get(
        industry_label,
        INDUSTRY_BACKDROP_MODIFIERS["general_services"],
    )


def industry_environment_anchors(industry_label: str) -> str | None:
    return INDUSTRY_ENVIRONMENT_ANCHORS.get(industry_label)


def hero_subject_guidance(industry_label: str, *, industry: str = "") -> str:
    vertical = resolve_vertical_subject_guidance(industry) if industry else None
    if vertical:
        return vertical
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
        archetype = resolve_scene_archetype(request, index)
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
        scene_archetype=resolve_scene_archetype(request, index),
        authenticity_mode=resolve_authenticity_mode(request),
    )
