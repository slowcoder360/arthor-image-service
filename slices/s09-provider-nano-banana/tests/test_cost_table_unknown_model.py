"""s09 AC-6: GoogleCostTable.cost_for(unknown) raises UnknownModelVersion."""

from __future__ import annotations

import pytest


def test_google_cost_for_unknown_model_raises():
    try:
        from app.providers.google_nano_banana import GoogleCostTable  # type: ignore[import-not-found]
        from app.providers.openai_image import UnknownModelVersion  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-6: GoogleCostTable / UnknownModelVersion must be importable ({exc})"
        )

    with pytest.raises(UnknownModelVersion):
        GoogleCostTable.cost_for("not-a-real-google-model-xyz", (1024, 1024))
