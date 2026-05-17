"""s03 AC-1: sign_body produces sha256=<hex> matching the python hmac reference."""

from __future__ import annotations

import hashlib
import hmac as _hmac

import pytest


def _import_sign_body():
    try:
        from app.auth.hmac import sign_body  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-1: `app.auth.hmac.sign_body` must be importable; not yet implemented ({exc})"
        )
    return sign_body


def _ref_sig(secret: str, body: bytes) -> str:
    digest = _hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_sign_body_prefix_is_sha256():
    sign_body = _import_sign_body()
    out = sign_body("secret", b"payload")
    assert out.startswith("sha256="), (
        "AC-1: sign_body must return a string with prefix 'sha256='"
    )


def test_sign_body_matches_python_hmac_reference():
    sign_body = _import_sign_body()
    secret = "shared-secret"
    body = b'{"hello":"world"}'
    assert sign_body(secret, body) == _ref_sig(secret, body), (
        "AC-1: sign_body must match `hmac.new(secret.encode(), body, sha256).hexdigest()` reference"
    )


def test_sign_body_deterministic():
    sign_body = _import_sign_body()
    a = sign_body("k", b"abc")
    b = sign_body("k", b"abc")
    assert a == b, "AC-1: sign_body must be deterministic for identical inputs"


def test_sign_body_different_secret_yields_different_sig():
    sign_body = _import_sign_body()
    a = sign_body("k1", b"abc")
    b = sign_body("k2", b"abc")
    assert a != b, "AC-1: sign_body must change when the secret changes"
