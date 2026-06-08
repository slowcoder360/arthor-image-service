"""Narrow hero-candidates request contract (W21-H)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, UUID4, model_validator

from app.payload.models import (
    BrandVisual,
    BrandVoice,
    Business,
    Location,
    Pack,
    PackProviderHint,
    PayloadV1,
    ReferencePolicy,
    Slot,
    SlotCamera,
    SlotCopyContext,
    SlotDimensions,
    SlotLayout,
    SlotLightingMood,
    SlotPeoplePolicy,
    SlotRoute,
    SlotSafeArea,
    SlotSection,
    SlotSubject,
    StyleProfileHint,
)

_TONE_ANGLE_INTENTS: dict[str, str] = {
    "search": "homepage hero emphasizing search intent and local discoverability",
    "story": "homepage hero emphasizing brand story and emotional trust",
    "offer": "homepage hero emphasizing offer clarity and conversion urgency",
}

_HERO_CALLBACK_URL = "https://arthor-ai.invalid/hero-candidates-no-callback"


class HeroVariantSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tone_angle: Literal["search", "story", "offer"] | None = None
    intent: Annotated[str, Field(min_length=8)] | None = None
    headline: str
    subhead: str | None = None

    @model_validator(mode="after")
    def _tone_or_intent(self) -> HeroVariantSlot:
        if self.tone_angle is None and self.intent is None:
            raise ValueError("each variant requires tone_angle or intent")
        return self


class HeroCandidatesRequest(BaseModel):
    """Narrow inbound shape for builder HeroTriad generation."""

    model_config = ConfigDict(extra="forbid")

    site_id: UUID4
    idempotency_key: Annotated[str, Field(min_length=8)]
    business: Business
    location: Location
    brand_voice: BrandVoice
    brand_visual: BrandVisual
    style_profile_hint: StyleProfileHint
    variants: Annotated[list[HeroVariantSlot], Field(min_length=3, max_length=3)]
    base_seed: int = 42
    default_provider_hint: PackProviderHint | None = None


def _variant_intent(variant: HeroVariantSlot) -> str:
    if variant.intent is not None:
        return variant.intent
    assert variant.tone_angle is not None
    return _TONE_ANGLE_INTENTS[variant.tone_angle]


def _variant_subject_primary(request: HeroCandidatesRequest, variant: HeroVariantSlot) -> str:
    locale = request.location.city or request.location.country
    return (
        f"homepage hero scene for {request.business.industry} in {locale} "
        f"— {variant.headline}"
    )


def variant_to_slot(request: HeroCandidatesRequest, variant: HeroVariantSlot, index: int) -> Slot:
    """Map one triad variant to a homepage hero slot (16:9 @ 1920×1080)."""
    return Slot(
        slot_id=f"hero_candidate_{index}",
        ordinal=index,
        page="/",
        route=SlotRoute(name=None, template=None, target_keyword=None),
        section=SlotSection(section_type="hero", section_instance_id=f"triad-{index}"),
        slot_kind="hero",
        intent=_variant_intent(variant),
        copy_context=SlotCopyContext(
            page_h1=variant.headline,
            section_heading=variant.subhead,
            body_excerpt=None,
            cta_label=None,
        ),
        subject=SlotSubject(
            primary=_variant_subject_primary(request, variant),
            setting="on-location or authentic business environment",
            props=[],
            people_policy=SlotPeoplePolicy(faces_allowed=False, notes=None),
        ),
        camera=SlotCamera(framing="wide", angle="eye-level", lens_feel="35mm"),
        lighting_mood=SlotLightingMood(mood_tokens=[], contrast="medium"),
        layout=SlotLayout(
            aspect_ratio="16:9",
            dimensions=SlotDimensions(w=1920, h=1080),
            safe_area=SlotSafeArea(mode="start", inset_pct=10),
            overlay_text_risk=True,
        ),
        count=1,
        provider_hint=request.default_provider_hint,
        condition_on_slot_id=None,
    )


def hero_request_to_payload_v1(request: HeroCandidatesRequest) -> PayloadV1:
    """Synthesize a minimal PayloadV1 for the shared style resolver + worker."""
    slots = [variant_to_slot(request, v, i) for i, v in enumerate(request.variants)]
    slot_ids = [s.slot_id for s in slots]
    return PayloadV1(
        payload_version="1.0",
        idempotency_key=request.idempotency_key,
        site_id=request.site_id,
        agent_run_id=uuid.uuid4(),
        callback_url=HttpUrl(_HERO_CALLBACK_URL),
        business=request.business,
        location=request.location,
        brand_voice=request.brand_voice,
        brand_visual=request.brand_visual,
        style_profile_hint=request.style_profile_hint,
        pack=Pack(
            pack_id=f"hero-candidates-{request.site_id}",
            base_seed=request.base_seed,
            slot_order=slot_ids,
            reference_policy=ReferencePolicy(
                hero_slot_id=slot_ids[0],
                condition_non_hero_slots_on_hero=False,
                allow_user_reference_conditioning=False,
            ),
            default_provider_hint=request.default_provider_hint,
        ),
        slots=slots,
    )
