"""s09 AC-6: GoogleCostTable.cost_for(known_model, dimensions) returns positive int."""

from __future__ import annotations

import pytest


def test_google_cost_for_known_model_returns_positive_int():
    try:
        from app.providers.google_nano_banana import GoogleCostTable  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: GoogleCostTable must be importable ({exc})")

    sample_model = next(iter(GoogleCostTable.RATES.keys()), None)
    assert sample_model is not None, (
        "AC-6: GoogleCostTable.RATES must declare at least one model"
    )
    sample_dim = next(iter(GoogleCostTable.RATES[sample_model].keys()), None)
    assert sample_dim is not None, (
        f"AC-6: GoogleCostTable.RATES[{sample_model}] must declare at least one dimension"
    )
    cents = GoogleCostTable.cost_for(sample_model, sample_dim)
    assert isinstance(cents, int) and cents > 0, (
        f"AC-6: cost_for(known) must return a positive int; got {cents!r}"
    )
