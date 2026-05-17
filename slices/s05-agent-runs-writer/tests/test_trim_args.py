"""s05 AC-5: trim_args strips long strings; preserves prompt_hash, numbers/bools/None; recurses."""

from __future__ import annotations

import pytest


def _import_trim():
    try:
        from app.runs.tool_calls import trim_args  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: trim_args must be importable ({exc})")
    return trim_args


def test_trim_args_replaces_long_strings_with_marker():
    trim_args = _import_trim()
    long_str = "x" * 1000
    out = trim_args({"prompt": long_str})
    assert out["prompt"] == {
        "_trimmed": True,
        "_original_len": 1000,
    }, "AC-5: long strings must be replaced with the documented marker dict"


def test_trim_args_preserves_short_strings():
    trim_args = _import_trim()
    out = trim_args({"prompt": "short"})
    assert out["prompt"] == "short", "AC-5: short strings must pass through untouched"


def test_trim_args_preserves_prompt_hash_always():
    trim_args = _import_trim()
    long_hash = "a" * 5000
    out = trim_args({"prompt_hash": long_hash})
    assert out["prompt_hash"] == long_hash, (
        "AC-5: prompt_hash must always be preserved regardless of length"
    )


def test_trim_args_recurses_into_nested_dicts():
    trim_args = _import_trim()
    long_str = "x" * 1000
    out = trim_args({"outer": {"inner": long_str}})
    assert out["outer"]["inner"] == {
        "_trimmed": True,
        "_original_len": 1000,
    }, "AC-5: trimming must recurse into nested dicts"


def test_trim_args_preserves_numbers_bools_none():
    trim_args = _import_trim()
    out = trim_args({"n": 42, "f": 3.14, "b": True, "x": None})
    assert out == {"n": 42, "f": 3.14, "b": True, "x": None}, (
        "AC-5: numbers, bools, and None must pass through untouched"
    )
