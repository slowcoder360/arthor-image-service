"""Double-submit cookie CSRF protection for inspector POST bodies."""

from __future__ import annotations

import hmac
import secrets

from fastapi import HTTPException, Request
from starlette.responses import Response

CSRF_COOKIE_NAME = "arthor_csrf_token"

__all__ = ["CSRF_COOKIE_NAME", "issue_csrf_token", "verify_csrf_token"]


def issue_csrf_token(
    response: Response,
    token: str | None = None,
    *,
    secure: bool = True,
) -> str:
    if token is None:
        token = secrets.token_urlsafe(32)
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        max_age=86400,
        httponly=True,
        secure=secure,
        samesite="strict",
    )
    return token


def verify_csrf_token(request: Request, form_token: str | None) -> None:
    if not form_token:
        raise HTTPException(status_code=403, detail="csrf_missing")
    cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if cookie is None:
        raise HTTPException(status_code=403, detail="csrf_missing")
    if not hmac.compare_digest(cookie.encode("utf-8"), form_token.encode("utf-8")):
        raise HTTPException(status_code=403, detail="csrf_mismatch")
