"""Deterministic post-generation QA gates for hero candidates (no LLM)."""

from __future__ import annotations

import io
from typing import Literal

from PIL import Image, ImageFilter, ImageOps

from app.quality.hero_failure_modes import FAILURE_MODES, pick_primary_failure_mode
from app.style.hero_viewports import MOBILE, HeroViewport

TOP_BAND_PCT = 0.14
_EDGE_DENSITY_THRESHOLD = 0.05
_SAFE_ZONE_EDGE_RATIO = 0.82
_SAFE_ZONE_VARIANCE_RATIO = 0.88


def _edge_map(img: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(img.convert("RGB"))
    return gray.filter(ImageFilter.FIND_EDGES)


def _region_edge_density(edge_img: Image.Image, box: tuple[int, int, int, int]) -> float:
    left, top, right, bottom = box
    if right <= left or bottom <= top:
        return 0.0
    crop = edge_img.crop(box)
    pixels = list(crop.get_flattened_data())
    if not pixels:
        return 0.0
    return sum(float(p) for p in pixels) / (len(pixels) * 255.0)


def _region_luminance_variance(rgb_img: Image.Image, box: tuple[int, int, int, int]) -> float:
    left, top, right, bottom = box
    if right <= left or bottom <= top:
        return 0.0
    crop = rgb_img.crop(box).convert("L")
    pixels = [float(p) for p in crop.get_flattened_data()]
    if not pixels:
        return 0.0
    mean = sum(pixels) / len(pixels)
    return sum((p - mean) ** 2 for p in pixels) / len(pixels)


def _desktop_regions(
    width: int,
    height: int,
    inset_pct: int,
) -> dict[str, tuple[int, int, int, int]]:
    top_h = max(1, int(height * TOP_BAND_PCT))
    inset_w = max(1, int(width * inset_pct / 100))
    center_x0 = int(width * 0.50)
    center_x1 = int(width * 0.85)
    center_y0 = int(height * 0.20)
    center_y1 = int(height * 0.80)
    return {
        "top_band": (0, 0, width, top_h),
        "left_safe": (0, top_h, inset_w, height),
        "center_ref": (center_x0, center_y0, center_x1, center_y1),
    }


def _mobile_regions(
    width: int,
    height: int,
    inset_pct: int,
) -> dict[str, tuple[int, int, int, int]]:
    top_h = max(1, int(height * inset_pct / 100))
    center_y0 = int(height * 0.55)
    center_y1 = int(height * 0.90)
    margin_x = int(width * 0.15)
    return {
        "top_band": (0, 0, width, top_h),
        "left_safe": (margin_x, 0, width - margin_x, top_h),
        "center_ref": (margin_x, center_y0, width - margin_x, center_y1),
    }


def _regions_for_viewport(
    width: int,
    height: int,
    *,
    viewport: HeroViewport,
    safe_area_inset_pct: int,
) -> dict[str, tuple[int, int, int, int]]:
    if viewport == MOBILE:
        return _mobile_regions(width, height, safe_area_inset_pct)
    return _desktop_regions(width, height, safe_area_inset_pct)


def run_hero_post_checks(
    image_bytes: bytes,
    *,
    viewport: HeroViewport = "desktop",
    safe_area_inset_pct: int = 40,
) -> list[str]:
    """Return ordered failure_mode tags (empty when all checks pass)."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = img.size
    regions = _regions_for_viewport(
        width,
        height,
        viewport=viewport,
        safe_area_inset_pct=safe_area_inset_pct,
    )
    edges = _edge_map(img)

    modes: list[str] = []
    top_edge = _region_edge_density(edges, regions["top_band"])
    if top_edge >= _EDGE_DENSITY_THRESHOLD:
        modes.append("rendered_ui")

    safe_edge = _region_edge_density(edges, regions["left_safe"])
    if safe_edge >= _EDGE_DENSITY_THRESHOLD:
        modes.append("rendered_text")

    center_edge = _region_edge_density(edges, regions["center_ref"])
    safe_var = _region_luminance_variance(img, regions["left_safe"])
    center_var = _region_luminance_variance(img, regions["center_ref"])
    if center_edge > 0 and center_var > 0:
        edge_ratio = safe_edge / center_edge
        var_ratio = safe_var / center_var
        if edge_ratio >= _SAFE_ZONE_EDGE_RATIO or var_ratio >= _SAFE_ZONE_VARIANCE_RATIO:
            modes.append("safe_zone_violation")

    return [m for m in modes if m in FAILURE_MODES]


def hero_post_check_failure_mode(check_modes: list[str]) -> str | None:
    """Pick the highest-priority post-check failure_mode, if any."""
    return pick_primary_failure_mode(*check_modes)


AUTO_RETRY_FAILURE_MODES = frozenset({"rendered_text", "safe_zone_violation"})
