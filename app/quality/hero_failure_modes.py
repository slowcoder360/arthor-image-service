"""Classify hero generation failures into structured ``failure_mode`` tags."""

from __future__ import annotations

FAILURE_MODES = frozenset(
    {
        "rendered_ui",
        "rendered_text",
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
