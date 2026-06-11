"""Pydantic v2 models for image request PayloadV1."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, UUID4

# --- Shared -----------------------------------------------------------------

HexColor = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$")]


def _pct01(x: float) -> float:
    return round(min(max(float(x), 0.0), 1.0), 10)


# --- Business / location ------------------------------------------------------


class Business(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_name: str
    industry: str
    icp_summary: str
    value_prop: str
    proof_points: list[str] = Field(default_factory=list)
    forbidden_subjects: list[str] = Field(default_factory=list)
    priority_services: list[str] = Field(default_factory=list)


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["local", "regional", "national"]
    city: str | None = None
    region: str | None = None
    country: Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
    service_areas: list[str] = Field(default_factory=list)


class BrandVoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tone: str
    notes: list[str] = Field(default_factory=list)
    style_direction: str = ""
    reference_likes: list[str] = Field(default_factory=list)
    do_not: list[str] = Field(default_factory=list)


class PaletteTone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: HexColor
    secondary: HexColor
    background: HexColor
    foreground: HexColor
    muted: HexColor


class Palette(BaseModel):
    model_config = ConfigDict(extra="forbid")

    light: PaletteTone
    dark: PaletteTone


class Typography(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sans: str
    heading: str


class CustomerReferenceAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    role: Literal["interior", "team", "product", "logo", "ambient"]
    url: HttpUrl
    palette_hex: list[HexColor] = Field(default_factory=list)
    usage_hint: str | None = None
    note: str | None = None
    likeness_consent: bool = False


class BrandVisual(BaseModel):
    model_config = ConfigDict(extra="forbid")

    palette: Palette
    typography: Typography
    register_default: Literal["photographic", "illustrated", "mixed"]
    logo_asset_id: str | None = None
    customer_reference_assets: list[CustomerReferenceAsset] = Field(default_factory=list)


class StyleProfileHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lighting: str
    camera_language: str = ""
    composition_rules: list[str] = Field(default_factory=list)
    color_grading: str = ""
    texture: str = ""
    era_mood: str | None = None
    do_not: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)


class ReferencePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hero_slot_id: str
    condition_non_hero_slots_on_hero: bool
    allow_user_reference_conditioning: bool


PackProviderHint = Literal["openai_image", "google_nano_banana"]


class Pack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pack_id: str
    base_seed: int
    slot_order: list[str]
    reference_policy: ReferencePolicy
    default_provider_hint: PackProviderHint | None = None


class SlotRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    template: str | None = None
    target_keyword: str | None = None


class SlotSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_type: str
    section_instance_id: str | None = None


class SlotCopyContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_h1: str | None = None
    section_heading: str | None = None
    body_excerpt: str | None = None
    cta_label: str | None = None


class SlotPeoplePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    faces_allowed: bool
    notes: str | None = None


class SlotSubject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: str
    setting: str
    props: list[str] = Field(default_factory=list)
    people_policy: SlotPeoplePolicy


class SlotCamera(BaseModel):
    model_config = ConfigDict(extra="forbid")

    framing: Literal["wide", "medium", "close", "aerial"]
    angle: Literal["eye-level", "low", "high"]
    lens_feel: Literal["24mm", "35mm", "50mm", "85mm", "unspecified"]


class SlotLightingMood(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mood_tokens: list[str] = Field(default_factory=list)
    contrast: Literal["low", "medium", "high"]


class SlotDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    w: Annotated[int, Field(ge=1)]
    h: Annotated[int, Field(ge=1)]


class SlotSafeArea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["start", "center", "end", "all"]
    inset_pct: Annotated[int, Field(ge=0, le=100)]


class SlotLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aspect_ratio: str
    dimensions: SlotDimensions
    safe_area: SlotSafeArea
    overlay_text_risk: bool


class Slot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_id: str
    ordinal: int
    page: str
    route: SlotRoute
    section: SlotSection
    slot_kind: Literal["hero", "section_accent", "card", "og", "portrait", "background"]
    intent: Annotated[str, Field(min_length=8)]
    copy_context: SlotCopyContext
    subject: SlotSubject
    camera: SlotCamera
    lighting_mood: SlotLightingMood
    layout: SlotLayout
    count: Annotated[int, Field(ge=1)]
    provider_hint: PackProviderHint | None = None
    condition_on_slot_id: str | None = None


class PayloadV1(BaseModel):
    """Authoritative Payload v1.0 schema (ADR-0010)."""

    model_config = ConfigDict(extra="forbid")

    payload_version: Literal["1.0"]
    idempotency_key: Annotated[str, Field(min_length=8)]
    site_id: UUID4
    agent_run_id: UUID4
    callback_url: HttpUrl
    business: Business
    location: Location
    brand_voice: BrandVoice
    brand_visual: BrandVisual
    style_profile_hint: StyleProfileHint
    pack: Pack
    slots: list[Slot] = Field(min_length=1)

    def payload_completeness_score(self) -> float:
        """0..1 score aligned with ValidationReport completeness (ADR-0010 MVP vs rich payload)."""

        p = self

        def _stripped(local: str | None) -> bool:
            return bool(local is not None and local.strip())

        shared_checks: list[Any] = [
            lambda: _stripped(p.business.site_name),
            lambda: _stripped(p.business.industry),
            lambda: _stripped(p.business.icp_summary),
            lambda: _stripped(p.business.value_prop),
            lambda: bool(p.business.proof_points is not None),  # struct present
            lambda: bool(p.brand_voice.tone.strip()),
            lambda: len(p.pack.slot_order) > 0,
            lambda: _stripped(p.style_profile_hint.lighting),
            lambda: len(p.style_profile_hint.do_not) > 0,
            lambda: any(_stripped(s.intent) for s in p.slots),
            lambda: all(s.layout.dimensions.w > 0 and s.layout.dimensions.h > 0 for s in p.slots),
            lambda: len(p.slots) > 0,
        ]

        discrim_checks = [
            lambda: len(p.business.proof_points) > 0,
            lambda: len(p.business.forbidden_subjects) > 0,
            lambda: len(p.business.priority_services) > 0,
            lambda: p.location.city is not None and _stripped(p.location.city),
            lambda: p.location.region is not None and _stripped(p.location.region),
            lambda: len(p.location.service_areas) > 0,
            lambda: len(p.brand_voice.notes) > 0,
            lambda: _stripped(p.brand_voice.style_direction),
            lambda: len(p.brand_voice.reference_likes) > 0,
            lambda: len(p.brand_voice.do_not) > 0,
            lambda: p.brand_visual.logo_asset_id is not None,
            lambda: len(p.brand_visual.customer_reference_assets) > 0,
            lambda: _stripped(p.style_profile_hint.camera_language),
            lambda: len(p.style_profile_hint.composition_rules) > 0,
            lambda: _stripped(p.style_profile_hint.color_grading),
            lambda: _stripped(p.style_profile_hint.texture),
            lambda: p.style_profile_hint.era_mood is not None,
            lambda: len(p.style_profile_hint.must_include) > 0,
            lambda: p.pack.default_provider_hint is not None,
            lambda: len(p.slots) >= 2,
            lambda: any(s.provider_hint is not None for s in p.slots),
            lambda: any(s.condition_on_slot_id is not None for s in p.slots),
            lambda: any(len(s.lighting_mood.mood_tokens) > 0 for s in p.slots),
            lambda: any(s.section.section_instance_id is not None for s in p.slots),
            lambda: any(len(s.subject.props) > 0 for s in p.slots),
            lambda: any(
                s.route.name is not None or s.route.template is not None or s.route.target_keyword is not None
                for s in p.slots
            ),
            lambda: any(
                sum(
                    (
                        _stripped(s.copy_context.page_h1),
                        _stripped(s.copy_context.section_heading),
                        _stripped(s.copy_context.body_excerpt),
                        _stripped(s.copy_context.cta_label),
                    )
                )
                >= 3
                for s in p.slots
            ),
            lambda: any(not s.layout.overlay_text_risk for s in p.slots),
        ]

        shared = sum(1 for f in shared_checks if f()) / len(shared_checks)
        discrim = sum(1 for f in discrim_checks if f()) / len(discrim_checks)
        return _pct01(shared * 0.38 + discrim * 0.62)
