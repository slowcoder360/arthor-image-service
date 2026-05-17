"""s08 AC-7: cost_for(unknown_model, ...) raises UnknownModelVersion."""

from __future__ import annotations

import pytest


def test_cost_for_unknown_model_raises():
    try:
        from app.providers.openai_image import (  # type: ignore[import-not-found]
            OpenAICostTable,
            UnknownModelVersion,
        )
    except ImportError as exc:
        pytest.fail(
            f"AC-7: OpenAICostTable / UnknownModelVersion must be importable ({exc})"
        )

    with pytest.raises(UnknownModelVersion):
        OpenAICostTable.cost_for("definitely-not-a-real-model-version-xyz", (1024, 1024))
