"""Classify hero generation failures into structured ``failure_mode`` tags."""

from __future__ import annotations

FAILURE_MODES = frozenset(
    {
        "rendered_ui",
        "rendered_text",
        "safe_zone_violation",
        "wrong_industry",
        "posed_faces_violation",
        "moderation_blocked",
        "provider_timeout",
        "palette_drift",
        "stale_orphaned_run",
        "provider_error",
        "unknown",
    }
)

_FAILURE_MODE_PRIORITY: tuple[str, ...] = (
    "moderation_blocked",
    "provider_timeout",
    "stale_orphaned_run",
    "provider_error",
    "rendered_text",
    "rendered_ui",
    "safe_zone_violation",
    "palette_drift",
    "wrong_industry",
    "posed_faces_violation",
    "unknown",
)


def pick_primary_failure_mode(*modes: str | None) -> str | None:
    """Choose a single failure_mode when multiple QA signals fire."""
    candidates = [m for m in modes if m]
    if not candidates:
        return None
    for label in _FAILURE_MODE_PRIORITY:
        if label in candidates:
            return label
    return candidates[0]


def classify_hero_failure(error: str | None, *, palette_drift: bool = False) -> str:
    """Map a provider or worker error string to a stable failure_mode label."""
    if palette_drift:
        return "palette_drift"
    if not error:
        return "unknown"
    low = error.lower()
    if "moderation" in low or "content_policy" in low or "blocked" in low:
        return "moderation_blocked"
    if "timeout" in low or "timed out" in low:
        return "provider_timeout"
    if "stale_orphaned" in low:
        return "stale_orphaned_run"
    return "provider_error"
