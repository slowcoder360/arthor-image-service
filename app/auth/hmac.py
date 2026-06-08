"""HMAC signing and verification (ADR-0006). Replay protection is intentionally out of scope."""

from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, Request

__all__ = ["require_hmac", "require_hmac_get", "sign_body", "verify_signature"]


def sign_body(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: bytes, header_value: str | None) -> bool:
    if header_value is None:
        return False
    if not header_value.startswith("sha256="):
        return False
    received_hex = header_value[len("sha256=") :]
    if len(received_hex) != 64:
        return False
    expected_hex = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received_hex, expected_hex)


async def require_hmac(req: Request) -> bytes:
    body = await req.body()
    req.state.raw_body = body

    services = getattr(req.app.state, "services", None)
    settings = getattr(services, "settings", None) if services else None
    secret = getattr(settings, "fastapi_arthor_shared_secret", None)

    if secret is None:
        raise HTTPException(status_code=503, detail="hmac_secret_unset")
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="empty_body")

    header_value = req.headers.get("X-Arthor-Signature")
    if not verify_signature(secret, body, header_value):
        raise HTTPException(status_code=401, detail="invalid_signature")

    return body


async def require_hmac_get(req: Request) -> bytes:
    """Verify HMAC for GET poll routes (empty body signed as ``b\"\"``)."""
    body = await req.body()
    req.state.raw_body = body

    services = getattr(req.app.state, "services", None)
    settings = getattr(services, "settings", None) if services else None
    secret = getattr(settings, "fastapi_arthor_shared_secret", None)

    if secret is None:
        raise HTTPException(status_code=503, detail="hmac_secret_unset")

    header_value = req.headers.get("X-Arthor-Signature")
    if not verify_signature(secret, body, header_value):
        raise HTTPException(status_code=401, detail="invalid_signature")

    return body
