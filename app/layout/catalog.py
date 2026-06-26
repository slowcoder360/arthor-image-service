"""Loader for the vendored hero layout-archetype static data (catalog + routing + map).

Pure data access — no scene resolution, payload, provider, or route imports — so this
module (and the resolver beside it) lift-and-shift unchanged into the planning brain.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

KNOWN_ARCHETYPES = frozenset(
    {
        "split_copy_image",
        "full_bleed_photo_overlay",
        "centered_copy_cta",
        "abstract_gradient_3d",
        "typographic_no_image",
        "product_screenshot",
    }
)

VALID_IMAGERY_TYPES = frozenset(
    {"real_photo", "product_ui", "generative_abstract", "abstract_or_none", "none"}
)

_DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "layout_archetypes"


class LayoutCatalogError(Exception):
    """Raised when vendored layout data is missing or malformed (fail fast)."""


@dataclass(frozen=True)
class LayoutArchetypeEntry:
    archetype: str
    imagery_type: str
    scene_catalog_eligible: bool
    structure: str
    avoid: tuple[str, ...]


@dataclass(frozen=True)
class BrandModeRouting:
    defaults: dict[str, str]
    fallbacks: dict[str, tuple[str, ...]]

    def default_for(self, brand_mode: str | None) -> str | None:
        if brand_mode is None:
            return None
        return self.defaults.get(brand_mode)

    def fallbacks_for(self, archetype: str) -> tuple[str, ...]:
        return self.fallbacks.get(archetype, ())


def _resolved_data_root() -> Path:
    """In-repo default unless LAYOUT_ARCHETYPE_DATA_PATH points elsewhere (dir or file)."""
    from app.config import get_settings

    configured = getattr(get_settings(), "layout_archetype_data_path", None)
    if configured:
        path = Path(configured)
        return path if path.is_dir() else path.parent
    return _DEFAULT_DATA_ROOT


def _read_yaml(root: Path, filename: str) -> dict:
    path = root / filename
    if not path.is_file():
        raise LayoutCatalogError(f"layout data file missing: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise LayoutCatalogError(f"layout data file must be a mapping: {path}")
    return data


def _parse_catalog(root: Path) -> tuple[LayoutArchetypeEntry, ...]:
    data = _read_yaml(root, "catalog.yaml")
    archetypes = data.get("archetypes")
    if not isinstance(archetypes, dict) or not archetypes:
        raise LayoutCatalogError("catalog.yaml must define a non-empty 'archetypes' mapping")
    entries: list[LayoutArchetypeEntry] = []
    for archetype, raw in archetypes.items():
        if archetype not in KNOWN_ARCHETYPES:
            raise LayoutCatalogError(f"unknown layout archetype id: {archetype!r}")
        imagery_type = (raw or {}).get("imagery_type")
        if imagery_type not in VALID_IMAGERY_TYPES:
            raise LayoutCatalogError(
                f"archetype {archetype!r} has invalid imagery_type {imagery_type!r}"
            )
        avoid = tuple(str(a) for a in (raw.get("avoid") or []))
        entries.append(
            LayoutArchetypeEntry(
                archetype=archetype,
                imagery_type=str(imagery_type),
                scene_catalog_eligible=bool(raw.get("scene_catalog_eligible")),
                structure=str(raw.get("structure") or ""),
                avoid=avoid,
            )
        )
    return tuple(entries)


@lru_cache(maxsize=1)
def load_layout_catalog() -> tuple[LayoutArchetypeEntry, ...]:
    return _parse_catalog(_resolved_data_root())


@lru_cache(maxsize=1)
def load_brand_mode_routing() -> BrandModeRouting:
    data = _read_yaml(_resolved_data_root(), "brand_mode_routing.yaml")
    defaults = {str(k): str(v) for k, v in (data.get("defaults") or {}).items()}
    fallbacks = {
        str(k): tuple(str(x) for x in (v or []))
        for k, v in (data.get("fallbacks") or {}).items()
    }
    return BrandModeRouting(defaults=defaults, fallbacks=fallbacks)


@lru_cache(maxsize=1)
def load_industry_brand_mode_map() -> tuple[tuple[str, str], ...]:
    data = _read_yaml(_resolved_data_root(), "industry_brand_mode.yaml")
    raw = data.get("map") or {}
    return tuple((str(k).lower(), str(v)) for k, v in raw.items())


@lru_cache(maxsize=1)
def _default_photo_layouts() -> frozenset[str]:
    return frozenset(
        e.archetype for e in _parse_catalog(_DEFAULT_DATA_ROOT) if e.scene_catalog_eligible
    )


PHOTO_LAYOUTS: frozenset[str] = _default_photo_layouts()


def archetype_ids() -> tuple[str, ...]:
    return tuple(sorted(e.archetype for e in load_layout_catalog()))


def clear_layout_cache() -> None:
    load_layout_catalog.cache_clear()
    load_brand_mode_routing.cache_clear()
    load_industry_brand_mode_map.cache_clear()
