"""s04 AC-3: MVP-only payload validates and scores in [0.35, 0.45]."""

from __future__ import annotations

import pytest

from _payload_fixtures import mvp_payload


def _import_pieces():
    try:
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
        from app.payload.validator import validate_payload  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-1/AC-3: `app.payload.{{models.PayloadV1, validator.validate_payload}}` must be importable ({exc})"
        )
    return PayloadV1, validate_payload


def test_mvp_payload_parses_and_scores_around_0_4():
    PayloadV1, validate_payload = _import_pieces()
    raw = mvp_payload()
    PayloadV1.model_validate(raw)
    payload, report = validate_payload(raw)
    assert 0.35 <= report.completeness_score <= 0.45, (
        f"AC-3: MVP payload must score in [0.35, 0.45], got {report.completeness_score}"
    )
    assert report.errors == [], (
        f"AC-3: MVP payload must validate cleanly, got errors {report.errors}"
    )
