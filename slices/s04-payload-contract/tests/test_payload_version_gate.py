"""s04 AC-4: payload_version gate — '1.0' accepted; '2.0' rejected; '1.1' warns."""

from __future__ import annotations

import pytest

from _payload_fixtures import mvp_payload


def _import_validator():
    try:
        from app.payload.validator import validate_payload  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: validate_payload must be importable ({exc})")
    return validate_payload


def test_version_1_0_accepted():
    validate_payload = _import_validator()
    raw = mvp_payload()
    raw["payload_version"] = "1.0"
    _, report = validate_payload(raw)
    assert report.errors == [], "AC-4: payload_version='1.0' must be accepted"


def test_version_2_0_rejected_with_clear_error():
    validate_payload = _import_validator()
    raw = mvp_payload()
    raw["payload_version"] = "2.0"
    _, report = validate_payload(raw)
    assert report.errors, (
        "AC-4: payload_version='2.0' must produce a structured error in v1"
    )


def test_version_1_1_accepted_with_warning():
    validate_payload = _import_validator()
    raw = mvp_payload()
    raw["payload_version"] = "1.1"
    payload, report = validate_payload(raw)
    assert report.warnings, (
        "AC-4: payload_version='1.1' (unknown 1.x) must be accepted with a warning per the versioning policy"
    )
