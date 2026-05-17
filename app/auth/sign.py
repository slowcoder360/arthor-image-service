"""Outbound HMAC headers for callbacks to arthor-ai."""

from __future__ import annotations

from app.auth.hmac import sign_body

__all__ = ["sign_outbound"]


def sign_outbound(secret: str, body: bytes) -> dict[str, str]:
    return {"X-Arthor-Signature": sign_body(secret, body)}
