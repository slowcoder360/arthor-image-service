"""s03 AC-6: sign_outbound output must verify under the inbound verify_signature."""

from __future__ import annotations

import pytest


def _import_pieces():
    try:
        from app.auth.hmac import verify_signature  # type: ignore[import-not-found]
        from app.auth.sign import sign_outbound  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-6: `app.auth.sign.sign_outbound` and `app.auth.hmac.verify_signature` must be importable ({exc})"
        )
    return sign_outbound, verify_signature


def test_outbound_sign_round_trips_with_inbound_verify():
    sign_outbound, verify_signature = _import_pieces()
    secret = "shared-secret"
    body = b'{"event":"image.completed"}'
    headers = sign_outbound(secret, body)
    assert "X-Arthor-Signature" in headers, (
        "AC-6: sign_outbound must return a dict containing 'X-Arthor-Signature'"
    )
    assert verify_signature(secret, body, headers["X-Arthor-Signature"]) is True, (
        "AC-6: outbound sig must verify under inbound verify_signature with the same secret"
    )


def test_outbound_sign_against_different_body_does_not_verify():
    sign_outbound, verify_signature = _import_pieces()
    secret = "shared-secret"
    body = b"original"
    headers = sign_outbound(secret, body)
    assert (
        verify_signature(secret, b"different", headers["X-Arthor-Signature"]) is False
    ), "AC-6: signature is tied to body bytes; verifying a different body must fail"
