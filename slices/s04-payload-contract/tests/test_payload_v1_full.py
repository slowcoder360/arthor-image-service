"""s04 AC-1 / AC-2: maximal payload round-trips through PayloadV1."""

from __future__ import annotations

import pytest

from _payload_fixtures import maximal_payload


def _import_payload_v1():
    try:
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-1: `app.payload.models.PayloadV1` must be importable; not yet implemented ({exc})"
        )
    return PayloadV1


def test_maximal_payload_parses():
    PayloadV1 = _import_payload_v1()
    raw = maximal_payload()
    PayloadV1.model_validate(raw)


def test_maximal_payload_dumps_match_input_modulo_coercion():
    PayloadV1 = _import_payload_v1()
    raw = maximal_payload()
    model = PayloadV1.model_validate(raw)
    dumped = model.model_dump(mode="json")

    assert dumped["payload_version"] == "1.0", "AC-1: payload_version must round-trip as '1.0'"
    assert dumped["idempotency_key"] == raw["idempotency_key"], (
        "AC-1: idempotency_key must round-trip"
    )
    assert dumped["business"]["industry"] == raw["business"]["industry"], (
        "AC-1: business.industry must round-trip"
    )
    assert (
        dumped["brand_visual"]["palette"]["light"]["primary"]
        == raw["brand_visual"]["palette"]["light"]["primary"]
    ), "AC-2: hex color must round-trip exactly"
    assert len(dumped["slots"]) == len(raw["slots"]), (
        "AC-1: slots[] length must round-trip"
    )
