"""s08 AC-7: OpenAICostTable.cost_for(known_model, dimensions) returns a positive int."""

from __future__ import annotations

import pytest


def test_cost_for_known_model_returns_positive_int():
    try:
        from app.providers.openai_image import OpenAICostTable  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-7: OpenAICostTable must be importable ({exc})")

    sample_model = next(iter(OpenAICostTable.RATES.keys()), None)
    assert sample_model is not None, (
        "AC-7: OpenAICostTable.RATES must declare at least one model"
    )
    sample_dim = next(iter(OpenAICostTable.RATES[sample_model].keys()), None)
    assert sample_dim is not None, (
        f"AC-7: OpenAICostTable.RATES[{sample_model}] must declare at least one dimension"
    )

    cents = OpenAICostTable.cost_for(sample_model, sample_dim)
    assert isinstance(cents, int) and cents > 0, (
        f"AC-7: cost_for(known) must return a positive int; got {cents!r}"
    )
