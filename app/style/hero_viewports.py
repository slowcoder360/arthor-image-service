"""Hero viewport specs — desktop landscape vs mobile portrait headers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HeroViewport = Literal["desktop", "mobile"]

DESKTOP: HeroViewport = "desktop"
MOBILE: HeroViewport = "mobile"


@dataclass(frozen=True)
class HeroViewportSpec:
    viewport: HeroViewport
    label: str
    width: int
    height: int
    aspect_ratio: str
    safe_area_mode: Literal["start", "end", "center"]
    default_inset_pct: int


VIEWPORT_SPECS: dict[HeroViewport, HeroViewportSpec] = {
    DESKTOP: HeroViewportSpec(
        viewport=DESKTOP,
        label="Desktop header",
        width=1536,
        height=1024,
        aspect_ratio="16:9",
        safe_area_mode="start",
        default_inset_pct=40,
    ),
    MOBILE: HeroViewportSpec(
        viewport=MOBILE,
        label="Mobile header",
        width=1024,
        height=1536,
        aspect_ratio="2:3",
        safe_area_mode="center",
        default_inset_pct=42,
    ),
}

# Mobile: stacked copy above image — quiet top band, subject in lower half.
MOBILE_TONE_COMPOSITION: dict[str, str] = {
    "search": (
        "Portrait mobile hero: primary subject in the lower half; "
        "upper ~42% softer contrast for stacked headline and subhead — "
        "full scene vertically, not an empty top void"
    ),
    "story": (
        "Portrait mobile hero: human connection anchored in the lower two-thirds; "
        "upper third gentler for trust-building copy stack — avoid blank top strip"
    ),
    "offer": (
        "Portrait mobile hero: outcome moment in the lower half; "
        "upper portion lower-contrast for offer headline, subhead, and CTA stack — "
        "balanced vertical composition"
    ),
}

MOBILE_COPY_HINTS: dict[str, str] = {
    "search": "search-intent copy stacks in the upper quiet zone",
    "story": "trust-building copy stacks in the upper quiet zone",
    "offer": "offer headline, subhead, and CTA stack in the upper quiet zone",
}


def resolve_viewport(raw: str | None) -> HeroViewport:
    if raw == MOBILE:
        return MOBILE
    return DESKTOP


def viewport_spec(viewport: HeroViewport) -> HeroViewportSpec:
    return VIEWPORT_SPECS[viewport]
