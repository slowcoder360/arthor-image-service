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
    SlotRoute,
    SlotSafeArea,
    SlotSection,
    SlotSubject,
    StyleProfileHint,
)
from app.style.hero_archetypes import (
    format_locale,
    safe_area_inset_pct,
    variant_people_policy,
    variant_setting,
    variant_subject_primary,
)

_TONE_ANGLE_INTENTS: dict[str, str] = {
    "search": "homepage hero emphasizing search intent and local discoverability",
    "story": "homepage hero emphasizing brand story and emotional trust",
    "offer": "homepage hero emphasizing offer clarity and conversion urgency",
}

_HERO_CALLBACK_URL = "https://arthor-ai.invalid/hero-candidates-no-callback"

HeroPayloadVersion = Literal["hero_candidates.1", "hero_candidates.2"]


class HeroCopyMetrics(BaseModel):
    """Spatial planning metrics — never sent verbatim to image providers."""

    model_config = ConfigDict(extra="forbid")

    headline_chars: int = 0
    has_subhead: bool = False
    has_cta: bool = False
    cta_chars: int = 0
    nav_count: int = 0


class HeroVariantCopyOverlay(BaseModel):
    """Marketing copy stored on run metadata only — not in provider prompts."""

    model_config = ConfigDict(extra="forbid")

    primary_cta: str | None = None
    secondary_cta: str | None = None
    supporting_text: str | None = None
    nav_labels: list[str] = Field(default_factory=list)


class HeroVariantSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tone_angle: Literal["search", "story", "offer"] | None = None
    intent: Annotated[str, Field(min_length=8)] | None = None
    headline: str
    subhead: str | None = None
    copy_metrics: HeroCopyMetrics | None = None
    copy_overlay: HeroVariantCopyOverlay | None = None

    @model_validator(mode="after")
    def _tone_or_intent(self) -> HeroVariantSlot:
        if self.tone_angle is None and self.intent is None:
            raise ValueError("each variant requires tone_angle or intent")
        return self

    @model_validator(mode="after")
    def _default_copy_metrics(self) -> HeroVariantSlot:
        if self.copy_metrics is not None:
            return self
        overlay = self.copy_overlay
        return self.model_copy(
            update={
                "copy_metrics": HeroCopyMetrics(
                    headline_chars=len(self.headline or ""),
                    has_subhead=bool(self.subhead and self.subhead.strip()),
                    has_cta=bool(overlay and overlay.primary_cta),
                    cta_chars=len(overlay.primary_cta) if overlay and overlay.primary_cta else 0,
                    nav_count=len(overlay.nav_labels) if overlay else 0,
                )
            }
        )


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
    payload_version: HeroPayloadVersion = "hero_candidates.1"


def _variant_intent(variant: HeroVariantSlot) -> str:
    if variant.intent is not None:
        return variant.intent
    assert variant.tone_angle is not None
    return _TONE_ANGLE_INTENTS[variant.tone_angle]


def variant_to_slot(request: HeroCandidatesRequest, variant: HeroVariantSlot, index: int) -> Slot:
    """Map one triad variant to a homepage hero slot (16:9 @ 1536×1024, provider-supported)."""
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
            cta_label=variant.copy_overlay.primary_cta if variant.copy_overlay else None,
        ),
        subject=SlotSubject(
            primary=variant_subject_primary(
                industry=request.business.industry,
                locale=format_locale(
                    city=request.location.city,
                    region=request.location.region,
                    country=request.location.country,
                ),
                tone_angle=variant.tone_angle,
                priority_services=list(request.business.priority_services),
            ),
            setting=variant_setting(variant.tone_angle),
            props=[],
            people_policy=variant_people_policy(variant.tone_angle),
        ),
        camera=SlotCamera(framing="wide", angle="eye-level", lens_feel="35mm"),
        lighting_mood=SlotLightingMood(mood_tokens=[], contrast="medium"),
        layout=SlotLayout(
            aspect_ratio="16:9",
            dimensions=SlotDimensions(w=1536, h=1024),
            safe_area=SlotSafeArea(mode="start", inset_pct=safe_area_inset_pct(variant.tone_angle)),
            overlay_text_risk=True,
        ),
        count=1,
        provider_hint=request.default_provider_hint,
        condition_on_slot_id=None,
    )


def build_hero_copy_overlay_metadata(request: HeroCandidatesRequest) -> list[dict[str, object]]:
    """Persist copy overlay fields on the run — never merged into provider prompts."""
    out: list[dict[str, object]] = []
    for index, variant in enumerate(request.variants):
        overlay = variant.copy_overlay
        metrics = variant.copy_metrics
        entry: dict[str, object] = {
            "variant_index": index,
            "tone_angle": variant.tone_angle,
            "headline": variant.headline,
            "subhead": variant.subhead,
        }
        if overlay:
            if overlay.primary_cta:
                entry["primary_cta"] = overlay.primary_cta
            if overlay.secondary_cta:
                entry["secondary_cta"] = overlay.secondary_cta
            if overlay.supporting_text:
                entry["supporting_text"] = overlay.supporting_text
            if overlay.nav_labels:
                entry["nav_labels"] = list(overlay.nav_labels)
        if metrics:
            entry["copy_metrics"] = metrics.model_dump(mode="json")
        out.append(entry)
    return out


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
