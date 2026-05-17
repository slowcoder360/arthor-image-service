"""s15 AC-4: cent counts render as dollars with two decimals (e.g. 4200 → `$42.00`)."""

from __future__ import annotations

import pytest


def test_format_cents_as_dollars_renders_dollars_two_decimals():
    try:
        from app.inspector.cost import format_cents_as_dollars  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: format_cents_as_dollars must be importable ({exc})")

    assert format_cents_as_dollars(4200) == "$42.00", (
        f"AC-4: 4200 cents must render as '$42.00'; got {format_cents_as_dollars(4200)!r}"
    )
    assert format_cents_as_dollars(42) == "$0.42", (
        f"AC-4: 42 cents must render as '$0.42'; got {format_cents_as_dollars(42)!r}"
    )
    assert format_cents_as_dollars(0) == "$0.00", (
        f"AC-4: 0 cents must render as '$0.00'; got {format_cents_as_dollars(0)!r}"
    )
