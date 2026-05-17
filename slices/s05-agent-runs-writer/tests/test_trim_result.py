"""s05 AC-5: trim_result preserves provider/model_version/seed/external_id even when long."""

from __future__ import annotations

import pytest


def _import_trim():
    try:
        from app.runs.tool_calls import trim_result  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: trim_result must be importable ({exc})")
    return trim_result


@pytest.mark.parametrize(
    "preserved_key", ["provider", "model_version", "seed", "external_id", "prompt_hash"]
)
def test_trim_result_preserves_key_even_if_long(preserved_key):
    trim_result = _import_trim()
    long_value = "z" * 5000
    out = trim_result({preserved_key: long_value})
    assert out[preserved_key] == long_value, (
        f"AC-5: trim_result must preserve `{preserved_key}` even when its value is long"
    )


def test_trim_result_strips_non_preserved_long_strings():
    trim_result = _import_trim()
    long_value = "z" * 5000
    out = trim_result({"raw_response": long_value})
    assert out["raw_response"] == {
        "_trimmed": True,
        "_original_len": 5000,
    }, "AC-5: non-preserved long strings must be replaced with the marker dict"
