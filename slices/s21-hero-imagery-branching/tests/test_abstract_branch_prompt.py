"""s21 AC-3: the new abstract hero prompt is deterministic, peopleless, and slop-free."""

from __future__ import annotations

import pytest


def test_abstract_prompt_is_deterministic_and_clean():
    try:
        from app.style.hero_abstract_prompt import build_abstract_hero_prompt  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: app.style.hero_abstract_prompt.build_abstract_hero_prompt must exist ({exc})")

    a = build_abstract_hero_prompt(palette_primary="#0A4B6F", seed=77, variant_index=0)
    b = build_abstract_hero_prompt(palette_primary="#0A4B6F", seed=77, variant_index=0)
    assert a == b, "AC-3: the abstract prompt must be deterministic for the same inputs"

    low = a.lower()
    assert "people" not in low and "person" not in low, (
        "AC-3: the abstract prompt must not request people"
    )
    assert "purple" not in low and "indigo" not in low, (
        "AC-3: the abstract prompt must avoid the indigo/purple gradient slop tell"
    )
