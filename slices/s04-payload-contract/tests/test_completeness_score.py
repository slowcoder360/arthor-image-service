"""s04 AC-9: maximal payload scores at least 0.5 above MVP payload."""

from __future__ import annotations

import pytest

from _payload_fixtures import maximal_payload, mvp_payload


def test_maximal_completeness_higher_than_mvp_by_at_least_half():
    try:
        from app.payload.validator import validate_payload  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-9: validate_payload must be importable ({exc})")

    _, mvp_report = validate_payload(mvp_payload())
    _, max_report = validate_payload(maximal_payload())

    diff = max_report.completeness_score - mvp_report.completeness_score
    assert diff >= 0.5, (
        f"AC-9: maximal completeness must exceed MVP by at least 0.5; got delta={diff}"
    )


def test_payload_v1_instance_completeness_score_method():
    try:
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-9: PayloadV1 must be importable ({exc})")

    payload = PayloadV1.model_validate(maximal_payload())
    score = payload.payload_completeness_score()
    assert isinstance(score, float), (
        "AC-9: PayloadV1.payload_completeness_score() must return a float"
    )
    assert 0.0 <= score <= 1.0, (
        f"AC-9: completeness score must be in [0.0, 1.0]; got {score}"
    )
