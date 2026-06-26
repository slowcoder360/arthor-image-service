"""s19 AC-1: brand_mode is an additive, optional field on the hero request."""

from __future__ import annotations

import pytest

from _layout_helpers import build_hero_request


def test_request_without_brand_mode_validates():
    try:
        from app.payload.hero_models import HeroCandidatesRequest  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: HeroCandidatesRequest must be importable ({exc})")

    HeroCandidatesRequest.model_validate(build_hero_request())


def test_request_with_brand_mode_validates_and_round_trips():
    try:
        from app.payload.hero_models import HeroCandidatesRequest  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: HeroCandidatesRequest must be importable ({exc})")

    req = HeroCandidatesRequest.model_validate(build_hero_request(brand_mode="agency"))
    assert req.brand_mode == "agency", (
        "AC-1: brand_mode must be an accepted additive field (extra=forbid otherwise rejects it)"
    )
