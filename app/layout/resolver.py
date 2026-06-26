"""Deterministic hero layout-archetype resolver (no LLM, no scene/payload coupling).

Given a brand_mode (and an optional industry for the v1 stopgap), pick the hero layout
archetype and its imagery contract. Reads only the vendored static data via app.layout.catalog.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from app.layout.catalog import (
    load_brand_mode_routing,
    load_industry_brand_mode_map,
    load_layout_catalog,
)

DECISION_VERSION = "1.0"
DEFAULT_ARCHETYPE = "split_copy_image"

BrandModeSource = Literal["explicit", "industry_stopgap", "default"]


@dataclass(frozen=True)
class HeroLayoutDecision:
    archetype: str
    imagery_type: str
    scene_catalog_eligible: bool
    brand_mode: str
    brand_mode_source: BrandModeSource
    imagery_fallbacks: tuple[str, ...] = field(default_factory=tuple)
    decision_version: str = DECISION_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["imagery_fallbacks"] = list(self.imagery_fallbacks)
        return data


def _entry_for(archetype: str):
    for entry in load_layout_catalog():
        if entry.archetype == archetype:
            return entry
    return None


def _derive_brand_mode_from_industry(industry: str) -> str | None:
    low = industry.lower()
    best: tuple[str, str] | None = None
    for key, brand_mode in load_industry_brand_mode_map():
        if key and key in low and (best is None or len(key) > len(best[0])):
            best = (key, brand_mode)
    return best[1] if best else None


def resolve_hero_layout_archetype(
    *,
    brand_mode: str | None = None,
    industry: str | None = None,
) -> HeroLayoutDecision:
    routing = load_brand_mode_routing()

    if brand_mode:
        mode: str | None = brand_mode
        source: BrandModeSource = "explicit"
    elif industry and (derived := _derive_brand_mode_from_industry(industry)):
        mode = derived
        source = "industry_stopgap"
    else:
        mode = None
        source = "default"

    archetype = routing.default_for(mode)
    if archetype is None:
        archetype = DEFAULT_ARCHETYPE
        source = "default"

    entry = _entry_for(archetype)
    imagery_type = entry.imagery_type if entry is not None else "none"
    scene_eligible = entry.scene_catalog_eligible if entry is not None else False

    return HeroLayoutDecision(
        archetype=archetype,
        imagery_type=imagery_type,
        scene_catalog_eligible=scene_eligible,
        brand_mode=mode or "default",
        brand_mode_source=source,
        imagery_fallbacks=routing.fallbacks_for(archetype),
    )
