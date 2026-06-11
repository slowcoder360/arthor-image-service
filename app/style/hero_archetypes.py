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
    backdrop="credible local professional service setting",
    trust="professional and customer in genuine consultation or helpful conversation",
    outcome="customer confident, relieved, or satisfied after service",
    experience="warm, approachable local business atmosphere with natural light",
    authority="experienced professional explaining options to an engaged customer",
    feel="trustworthy, approachable, locally rooted",
    avoid_extra=("generic stock office", "empty workspace as hero"),
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
        backdrop="measured professional law office — human consultation, not empty conference room",
        trust="attorney listening to and helping a client across a desk; mutual focus",
        outcome="client relieved and confident after consultation",
        experience="authoritative yet approachable office warmth; subtle wood and natural light",
        authority="attorney reviewing case details with client engaged in discussion",
        feel="authoritative, measured, trustworthy counsel",
        avoid_extra=(
            "empty conference room as hero",
            "library shelves or gavel as focal point",
            "courtroom drama",
            "judge robes",
        ),
    ),
    IndustryContext(
        match_keys=("hvac", "plumb", "electric", "contractor", "roofing"),
        label="home_services",
        backdrop="well-maintained home — comfort and protection, not equipment hero",
        trust="technician in respectful conversation with homeowner; honest local expertise",
        outcome="comfortable family relaxed at home; protected, cool, or safe feeling",
        experience="warm natural light in a cared-for home interior or exterior",
        authority="skilled tradesperson demonstrating expertise while homeowner watches with confidence",
        feel="reliable, local, no-nonsense expertise",
        avoid_extra=(
            "air conditioner or roof as hero subject",
            "technician van wrap mockup",
            "tools or equipment as focal point",
            "overposed uniform models",
        ),
    ),
    IndustryContext(
        match_keys=("health", "medical", "clinic", "therapy", "chiro"),
        label="healthcare",
        backdrop="welcoming healthcare office — human-centered, not treatment-room equipment hero",
        trust="provider and patient in reassuring consultation; human connection",
        outcome="patient at ease, genuine relief or progress moment",
        experience="soft natural light, relaxed patient, spa-like calm without clinical coldness",
        authority="provider reviewing scans or plan with patient engaged",
        feel="reassuring, competent, patient-centered",
        avoid_extra=(
            "empty therapy couch or exam table as hero",
            "explicit medical procedures",
            "clinical hardware as focal point",
            "identifiable patient close-up",
        ),
    ),
    _DEFAULT,
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
