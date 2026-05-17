"""s03 AC-2: verify_signature uses constant-time compare; rejects bad inputs cleanly."""

from __future__ import annotations

import hashlib
import hmac as _hmac

import pytest


def _import_pieces():
    try:
        from app.auth.hmac import sign_body, verify_signature  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-2: `app.auth.hmac.{{sign_body,verify_signature}}` must be importable ({exc})"
        )
    return sign_body, verify_signature


def test_verify_signature_valid_returns_true():
    sign_body, verify_signature = _import_pieces()
    secret, body = "k", b"hello"
    sig = sign_body(secret, body)
    assert verify_signature(secret, body, sig) is True, (
        "AC-2: a valid signature must verify True"
    )


def test_verify_signature_missing_header_returns_false():
    _, verify_signature = _import_pieces()
    assert verify_signature("k", b"hello", None) is False, (
        "AC-2: header_value=None must return False (never raise)"
    )


def test_verify_signature_wrong_prefix_returns_false():
    _, verify_signature = _import_pieces()
    digest = _hmac.new(b"k", b"hello", hashlib.sha256).hexdigest()
    assert verify_signature("k", b"hello", f"sha512={digest}") is False, (
        "AC-2: prefix other than 'sha256=' must return False"
    )


def test_verify_signature_wrong_hex_returns_false():
    _, verify_signature = _import_pieces()
    bogus = "sha256=" + ("0" * 64)
    assert verify_signature("k", b"hello", bogus) is False, (
        "AC-2: incorrect hex digest must return False"
    )


def test_verify_signature_secret_mismatch_returns_false():
    sign_body, verify_signature = _import_pieces()
    sig = sign_body("k1", b"hello")
    assert verify_signature("k2", b"hello", sig) is False, (
        "AC-2: signature signed by a different secret must return False"
    )


def test_verify_signature_tampered_body_returns_false():
    sign_body, verify_signature = _import_pieces()
    sig = sign_body("k", b"hello")
    assert verify_signature("k", b"hello-tampered", sig) is False, (
        "AC-2: tampered body must return False"
    )
