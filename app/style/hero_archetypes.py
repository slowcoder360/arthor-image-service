"""Shared industry archetypes and tone rules for hero slot mapping + prompt compile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.payload.models import SlotPeoplePolicy

ToneAngle = Literal["search", "story", "offer"] | None

TONE_COMPOSITION: dict[str, str] = {
    "search": (
        "subject and detail weighted to the center-right third; "
        "left 40% kept visually quiet for search-intent headline overlay"
    ),
    "story": (
        "subject and emotional focal point in the right third; "
        "left 40% soft negative space for trust-building headline overlay"
    ),
    "offer": (
        "subject anchored lower-right; "
        "upper-left 45% clear and lower-contrast for offer headline, subhead, and CTA overlay"
    ),
}

TONE_PEOPLE: dict[str, str] = {
    "search": "no posed people; empty or incidental blurred figures only",
    "story": "no direct-to-camera portraits; optional soft profile or empty room",
    "offer": "no full patient/customer portrait; empty focal area for CTA overlay",
}


@dataclass(frozen=True)
class IndustryArchetype:
    """Match keys are lowercase substrings tested against ``business.industry``."""

    match_keys: tuple[str, ...]
    label: str
    scene: str
    anchors: tuple[str, ...]
    feel: str
    avoid_extra: tuple[str, ...] = ()


_DEFAULT: IndustryArchetype = IndustryArchetype(
    match_keys=(),
    label="general_services",
    scene="credible local professional service environment",
    anchors=("authentic workspace", "natural materials", "real-world detail"),
    feel="trustworthy, approachable, locally rooted",
)

INDUSTRY_ARCHETYPES: tuple[IndustryArchetype, ...] = (
    IndustryArchetype(
        match_keys=("dental", "dentist", "orthodont"),
        label="dental",
        scene="modern dental practice interior",
        anchors=(
            "dental operatory or welcoming reception",
            "dental chair silhouette or instrument tray",
            "warm clinical cleanliness without hospital sterility",
        ),
        feel="calm, hygienic, family-friendly dentistry",
        avoid_extra=("generic spa/wellness lobby", "medical hospital corridor"),
    ),
    IndustryArchetype(
        match_keys=("legal", "law", "attorney", "lawyer"),
        label="legal",
        scene="professional law office interior",
        anchors=(
            "library shelves or conference table",
            "subtle wood and leather textures",
            "confident professional atmosphere",
        ),
        feel="authoritative, measured, trustworthy counsel",
        avoid_extra=("courtroom drama", "judge robes", "gavel clichés"),
    ),
    IndustryArchetype(
        match_keys=("hvac", "plumb", "electric", "contractor", "roofing"),
        label="home_services",
        scene="residential service context",
        anchors=(
            "well-maintained home interior or exterior",
            "technician tools implied but not posed advertisement",
            "honest trades craftsmanship",
        ),
        feel="reliable, local, no-nonsense expertise",
        avoid_extra=("stock van wrap mockups", "overposed uniform models"),
    ),
    IndustryArchetype(
        match_keys=("health", "medical", "clinic", "therapy", "chiro"),
        label="healthcare",
        scene="welcoming healthcare office",
        anchors=(
            "clean treatment or consultation room",
            "soft natural light",
            "human-centered care environment",
        ),
        feel="reassuring, competent, patient-centered",
        avoid_extra=("explicit procedures", "patient faces in close-up"),
    ),
    _DEFAULT,
)


def resolve_industry(industry: str) -> IndustryArchetype:
    low = industry.lower()
    for archetype in INDUSTRY_ARCHETYPES:
        if not archetype.match_keys:
            continue
        if any(k in low for k in archetype.match_keys):
            return archetype
    return _DEFAULT


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
    archetype = resolve_industry(industry)
    anchors = ", ".join(archetype.anchors[:3])
    tone = tone_angle or "search"
    people = TONE_PEOPLE.get(tone, TONE_PEOPLE["search"])
    base = (
        f"{archetype.scene} in {locale} ({archetype.label}); "
        f"visual anchors: {anchors}; not a generic spa or stock wellness lobby"
    )
    if priority_services:
        svc = ", ".join(priority_services[:2])
        base += f"; priority services: {svc}"
    return f"{base}. People policy: {people}."


def variant_setting(tone_angle: ToneAngle) -> str:
    if tone_angle and tone_angle in TONE_COMPOSITION:
        return TONE_COMPOSITION[tone_angle]
    return "subject off-center with generous negative space reserved for homepage copy overlay"


def variant_people_policy(tone_angle: ToneAngle) -> SlotPeoplePolicy:
    tone = tone_angle or "search"
    notes = TONE_PEOPLE.get(tone, TONE_PEOPLE["search"])
    return SlotPeoplePolicy(faces_allowed=False, notes=notes)
