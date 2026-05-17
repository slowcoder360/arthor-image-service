"""s06 AC-2: DEFAULT_DO_NOT is a tuple of exactly the 10 ADR-0009 strings in order."""

from __future__ import annotations

import pytest


EXPECTED = (
    "stock-photo aesthetic",
    "AI-uncanny faces",
    "synthetic AI guru aesthetic",
    "fake corporate office",
    "generic AI-influencer template",
    "saturated neon gradients",
    "warped or extra fingers",
    "broken/distorted text",
    "obvious AI watermarks",
    "fluorescent over-saturation",
)


def test_default_do_not_is_a_tuple_of_ten_strings_in_order():
    try:
        from app.style.defaults import DEFAULT_DO_NOT  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-2: `app.style.defaults.DEFAULT_DO_NOT` must be importable ({exc})"
        )
    assert isinstance(DEFAULT_DO_NOT, tuple), (
        "AC-2: DEFAULT_DO_NOT must be a tuple (immutable)"
    )
    assert DEFAULT_DO_NOT == EXPECTED, (
        f"AC-2: DEFAULT_DO_NOT must equal the 10 ADR-0009 strings in order; got {DEFAULT_DO_NOT!r}"
    )
