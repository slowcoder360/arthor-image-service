"""Hero job templates, industry backdrop modifiers, and tone rules for prompt compile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.payload.models import SlotPeoplePolicy

ToneAngle = Literal["search", "story", "offer"] | None
HeroJob = Literal["trust", "outcome", "experience", "authority"]

TONE_TO_JOB: dict[str, HeroJob] = {
    "search": "trust",
    "story": "experience",
    "offer": "outcome",
}

# Left safe zone: softer contrast for copy legibility — not a blank void.
TONE_COMPOSITION: dict[str, str] = {
    "search": (
        "Primary human subject and emotional focal point in the center-right two-thirds; "
        "left third slightly softer in contrast and detail so headline copy remains legible — "
        "continue natural environment across the full width; never a blank wall or empty left half"
    ),
    "story": (
        "Human connection moment anchored in the right half; "
        "left third gentler contrast for trust-building copy — "
        "keep warmth and contextual detail across frame; avoid sterile empty space on the left"
    ),
    "offer": (
        "Outcome or relief moment anchored lower-right; "
        "upper-left and lower-left slightly lower-contrast for offer copy and CTA — "
        "still a full, balanced scene; do not sacrifice subject for an oversized empty copy zone"
    ),
}

TONE_PEOPLE: dict[str, str] = {
    "search": (
        "candid human trust moment — provider and customer in natural consultation or warm interaction; "
        "soft three-quarter or profile acceptable; not stock grin at camera; not empty room"
    ),
    "story": (
        "authentic human connection in context — conversation, reassurance, or relaxed experience; "
        "natural profiles and gestures; not posed advertisement; not equipment as hero"
    ),
    "offer": (
        "visible outcome or relief — confident smile, family at ease, customer satisfied; "
        "subject stays right-weighted; not empty focal area; not direct-to-camera stock portrait"
    ),
}

GLOBAL_HERO_AVOID: tuple[str, ...] = (
    "dental chair or operatory as hero subject",
    "empty equipment as hero subject",
    "blank left half or empty void reserved for copy",
    "sterile copy-zone wall with no scene continuity",
    "stock smile staring at camera",
    "website mockups",
    "rendered words or signage text",
)


@dataclass(frozen=True)
class IndustryContext:
    """Industry provides backdrop + job-specific scenes; never equipment-as-hero."""

    match_keys: tuple[str, ...]
    label: str
    backdrop: str
    trust: str
    outcome: str
    experience: str
    authority: str
    feel: str
    avoid_extra: tuple[str, ...] = ()


_DEFAULT: IndustryContext = IndustryContext(
    match_keys=(),
    label="general_services",
    backdrop="credible local professional service setting — consult or on-site service, not domestic leisure",
    trust="professional and customer in genuine consultation or helpful on-site conversation",
    outcome="customer confident, relieved, or satisfied after service with visible service context",
    experience="warm, approachable business atmosphere with natural light; provider and customer engaged",
    authority="experienced professional explaining options to an engaged customer",
    feel="trustworthy, approachable, locally rooted",
    avoid_extra=(
        "generic stock office",
        "empty workspace as hero",
        "kitchen table lifestyle",
        "family on couch",
        "residential leisure with no service cues",
    ),
)

INDUSTRY_CONTEXTS: tuple[IndustryContext, ...] = (
    IndustryContext(
        match_keys=("dental", "dentist", "orthodont"),
        label="dental",
        backdrop="bright modern dental clinic — reception or consult area; no operatory or chair in frame",
        trust="dentist and patient in calm face-to-face consultation; conversation and trust, equipment absent or fully out of frame",
        outcome="confident natural smile, parent and child at ease after visit, genuine relief — never posed with dental chair",
        experience="relaxed patient in welcoming setting, soft natural light — human warmth, not clinical equipment",
        authority="dentist explaining treatment plan while patient listens; whiteboard or tablet ok, never operatory hero shot",
        feel="calm, hygienic, family-friendly dentistry",
        avoid_extra=(
            "empty dental chair as focal point",
            "dental operatory or instrument tray as hero",
            "x-ray machine or clinical hardware hero",
            "reception desk as main subject",
            "generic spa/wellness lobby",
            "residential home interior",
            "living room or kitchen backdrop",
            "domestic furniture masquerading as clinic",
        ),
    ),
    IndustryContext(
        match_keys=("legal", "law", "attorney", "lawyer"),
        label="legal",
        backdrop="measured professional law office — attorney and client in consultation, not empty conference room",
        trust="attorney listening to and helping a single client across a desk; mutual focus, professional attire",
        outcome="client relieved and confident after consultation at desk or table",
        experience="authoritative yet approachable office warmth; subtle wood and natural light; one-on-one counsel",
        authority="attorney reviewing case details with client engaged in discussion — two adults, not a family group",
        feel="authoritative, measured, trustworthy counsel",
        avoid_extra=(
            "empty conference room as hero",
            "library shelves or gavel as focal point",
            "courtroom drama",
            "judge robes",
            "family group walking through doorway",
            "multiple unrelated people as if a family",
            "residential home interior",
            "living room or kitchen backdrop",
        ),
    ),
    IndustryContext(
        match_keys=("hvac", "plumb", "electric", "contractor", "roofing"),
        label="home_services",
        backdrop=(
            "on-site home service visit — technician with homeowner at entryway, exterior, or utility area; "
            "service interaction visible, not passive domestic leisure"
        ),
        trust="technician in uniform or workwear respectfully consulting homeowner at the door or beside equipment area",
        outcome="homeowner relieved after completed service — visible comfort outcome with technician or service context nearby",
        experience="technician and homeowner in active conversation during a service visit; natural daylight at home exterior or entry",
        authority="skilled tradesperson explaining work to attentive homeowner on-site — tools secondary, people primary",
        feel="reliable, local, no-nonsense expertise",
        avoid_extra=(
            "family on couch or sofa with no service interaction",
            "living room leisure scene",
            "family walking through front door without technician",
            "kitchen table lifestyle",
            "air conditioner or roof as hero subject",
            "technician van wrap mockup",
            "tools or equipment as focal point",
            "overposed uniform models",
        ),
    ),
    IndustryContext(
        match_keys=("health", "medical", "clinic", "therapy", "chiro", "physical therapy"),
        label="healthcare",
        backdrop="welcoming clinic or therapy office — clean consult room, not gym or residential interior",
        trust="provider and patient in reassuring consultation; provider in professional clinical attire",
        outcome="patient at ease after consult — progress or relief moment in clinic setting",
        experience="calm clinic consult with provider and patient; soft natural light; professional dress, not athletic wear",
        authority="provider reviewing plan with patient at desk or table — clinical office cues in background",
        feel="reassuring, competent, patient-centered",
        avoid_extra=(
            "gym bags or athletic wear",
            "fitness studio or gym aesthetic",
            "polo shirt casual gym look",
            "empty therapy couch or exam table as hero",
            "explicit medical procedures",
            "clinical hardware as focal point",
            "residential home interior",
            "living room or kitchen backdrop",
        ),
    ),
    IndustryContext(
        match_keys=("landscap", "lawn", "garden", "mow", "arbor", "tree care", "yard"),
        label="outdoor_services",
        backdrop="outdoor residential or commercial property — maintained lawn, garden, or yard in natural daylight",
        trust="landscaping professional or crew consulting homeowner in the yard; visible green space and work context",
        outcome="well-kept yard and satisfied homeowner outdoors; landscaping results visible",
        experience="active outdoor maintenance or design conversation on the property; crew or pro with homeowner",
        authority="experienced landscaper walking the property with homeowner reviewing the plan",
        feel="capable, local, outdoor craft",
        avoid_extra=(
            "kitchen table or indoor domestic scene",
            "family on couch with no outdoor work",
            "generic home interior leisure",
            "living room backdrop",
        ),
    ),
)

# Backward-compatible alias for compiler metadata fields.
IndustryArchetype = IndustryContext
INDUSTRY_ARCHETYPES = INDUSTRY_CONTEXTS


def resolve_hero_job(tone_angle: ToneAngle) -> HeroJob:
    tone = tone_angle or "search"
    return TONE_TO_JOB.get(tone, "trust")


def resolve_industry(industry: str) -> IndustryContext:
    low = industry.lower()
    for ctx in INDUSTRY_CONTEXTS:
        if not ctx.match_keys:
            continue
        if any(k in low for k in ctx.match_keys):
            return ctx
    return _DEFAULT


def hero_job_scene(ctx: IndustryContext, job: HeroJob) -> str:
    return getattr(ctx, job)


def format_locale(*, city: str | None, region: str | None, country: str) -> str:
    if city and region:
        return f"{city}, {region}"
    if city:
        return city
    return country


def safe_area_inset_pct(tone_angle: ToneAngle) -> int:
    if tone_angle == "offer":
        return 45
    return 40


def variant_subject_primary(
    *,
    industry: str,
    locale: str,
    tone_angle: ToneAngle,
    priority_services: list[str],
) -> str:
    ctx = resolve_industry(industry)
    job = resolve_hero_job(tone_angle)
    scene = hero_job_scene(ctx, job)
    tone = tone_angle or "search"
    people = TONE_PEOPLE.get(tone, TONE_PEOPLE["search"])
    base = (
        f"Hero job ({job}): {scene} in {ctx.backdrop}, {locale} ({ctx.label}); "
        f"show what the customer wants, not what the business owns"
    )
    if priority_services:
        svc = ", ".join(priority_services[:2])
        base += f"; priority services: {svc}"
    return f"{base}. People policy: {people}."


def variant_setting(tone_angle: ToneAngle) -> str:
    if tone_angle and tone_angle in TONE_COMPOSITION:
        return TONE_COMPOSITION[tone_angle]
    return (
        "human subject right-weighted with softer left contrast for copy overlay — "
        "full scene across frame, not empty left half"
    )


def variant_people_policy(tone_angle: ToneAngle) -> SlotPeoplePolicy:
    tone = tone_angle or "search"
    notes = TONE_PEOPLE.get(tone, TONE_PEOPLE["search"])
    return SlotPeoplePolicy(faces_allowed=True, notes=notes)
