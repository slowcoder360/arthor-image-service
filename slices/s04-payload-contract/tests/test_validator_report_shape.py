"""s04 AC-3: ValidationReport shape; bytes input that aren't JSON raise; valid issues never raise."""

from __future__ import annotations

import json

import pytest

from _payload_fixtures import mvp_payload


def _import_pieces():
    try:
        from app.payload.validator import (  # type: ignore[import-not-found]
            ValidationReport,
            validate_payload,
        )
    except ImportError as exc:
        pytest.fail(
            f"AC-3: `app.payload.validator.{{validate_payload, ValidationReport}}` must be importable ({exc})"
        )
    return validate_payload, ValidationReport


def test_validator_returns_validation_report_instance():
    validate_payload, ValidationReport = _import_pieces()
    raw = mvp_payload()
    _, report = validate_payload(raw)
    assert isinstance(report, ValidationReport), (
        "AC-3: validate_payload() must return (PayloadV1, ValidationReport)"
    )
    assert hasattr(report, "errors"), "AC-3: ValidationReport.errors must exist"
    assert hasattr(report, "warnings"), "AC-3: ValidationReport.warnings must exist"
    assert hasattr(report, "completeness_score"), (
        "AC-3: ValidationReport.completeness_score must exist"
    )
    assert isinstance(report.completeness_score, float), (
        "AC-3: completeness_score must be a float"
    )


def test_validator_does_not_raise_on_validation_failures():
    validate_payload, _ = _import_pieces()
    bad = {"payload_version": "1.0", "idempotency_key": "abcd1234"}
    _, report = validate_payload(bad)
    assert report.errors, (
        "AC-3: missing required fields must surface as ValidationReport.errors, not exceptions"
    )


def test_validator_raises_on_malformed_json_bytes():
    validate_payload, _ = _import_pieces()
    with pytest.raises(Exception):
        validate_payload(b"{ not json ")


def test_validator_accepts_bytes_with_valid_json():
    validate_payload, _ = _import_pieces()
    raw_bytes = json.dumps(mvp_payload()).encode("utf-8")
    payload, report = validate_payload(raw_bytes)
    assert report.errors == [], (
        "AC-3: bytes input with valid JSON must validate identically to dict input"
    )
