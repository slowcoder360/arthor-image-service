"""Default seeds for StyleProfile resolution (ADR-0009)."""

from __future__ import annotations

DEFAULT_DO_NOT: tuple[str, ...] = (
    "stock-photo aesthetic",
    "AI-uncanny faces",
    "synthetic AI guru aesthetic",
    "fake corporate office",
    "generic AI-influencer template",
    "saturated neon gradients",
    "warped or extra fingers",
    "broken/distorted text",
    "obvious AI watermarks",
    "fluorescent over-saturation",
)

DEFAULT_LIGHTING_BY_REGISTER: dict[str, str] = {
    "photographic": "warm natural light, golden hour",
    "illustrated": "even editorial flat lighting",
    "mixed": "soft directional natural light",
}

DEFAULT_COMPOSITION: tuple[str, ...] = (
    "rule-of-thirds",
    "mid-distance framing",
    "negative space in safe_area",
)

INDUSTRY_DO_NOT_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "healthcare": (
        "no patient faces",
        "no medical procedures shown explicitly",
    ),
    "legal": (
        "no fake court / courtroom imagery",
        "no impersonation of judges or jurors",
    ),
    "finance": (
        "no fabricated charts or growth claims",
    ),
}
