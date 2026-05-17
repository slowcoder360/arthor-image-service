"""s08 AC-1: ProviderResult dataclass has the 11 documented fields."""

from __future__ import annotations

import dataclasses

import pytest


REQUIRED_FIELDS = {
    "image_bytes",
    "width",
    "height",
    "seed",
    "provider",
    "model_version",
    "cost_cents",
    "latency_ms",
    "external_id",
    "response_shape",
    "determinism_level",
}


def test_provider_result_has_all_documented_fields():
    try:
        from app.providers.protocol import ProviderResult  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-1: `app.providers.protocol.ProviderResult` must be importable ({exc})"
        )
    assert dataclasses.is_dataclass(ProviderResult), (
        "AC-1: ProviderResult must be a dataclass"
    )
    fields = {f.name for f in dataclasses.fields(ProviderResult)}
    missing = REQUIRED_FIELDS - fields
    assert not missing, (
        f"AC-1: ProviderResult is missing fields {missing}; got {sorted(fields)}"
    )
