"""s04 AC-6: canonical-JSON hash is stable across key reorderings."""

from __future__ import annotations

import hashlib
import json

import pytest

from _payload_fixtures import mvp_payload


def test_canonical_hash_stable_across_key_reorder():
    try:
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: PayloadV1 must be importable ({exc})")

    raw_a = mvp_payload()
    raw_b = mvp_payload()

    flipped: dict = {}
    for key in reversed(list(raw_b.keys())):
        flipped[key] = raw_b[key]

    payload_a = PayloadV1.model_validate(raw_a)
    payload_b = PayloadV1.model_validate(flipped)

    canonical_a = json.dumps(
        payload_a.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    canonical_b = json.dumps(
        payload_b.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    hash_a = hashlib.sha256(canonical_a.encode()).hexdigest()
    hash_b = hashlib.sha256(canonical_b.encode()).hexdigest()
    assert hash_a == hash_b, (
        "AC-6: canonical-JSON sha256 must be stable across key-order permutations"
    )
