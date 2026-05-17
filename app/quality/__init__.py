"""Quality checks on generated imagery."""

from __future__ import annotations

from app.quality.palette_variance import check_palette_drift

__all__ = ["check_palette_drift"]
