"""s06 AC-8: PROMPT_TEMPLATE_VERSION constant equals '1.0'."""

from __future__ import annotations

import pytest


def test_prompt_template_version_constant_is_one_dot_zero():
    try:
        from app.style.prompts import PROMPT_TEMPLATE_VERSION  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-8: PROMPT_TEMPLATE_VERSION must be importable ({exc})")
    assert PROMPT_TEMPLATE_VERSION == "1.0", (
        f"AC-8: PROMPT_TEMPLATE_VERSION must equal '1.0' (bumping requires Justin + new ADR); "
        f"got {PROMPT_TEMPLATE_VERSION!r}"
    )
