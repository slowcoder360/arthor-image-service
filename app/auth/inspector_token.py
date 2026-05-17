"""Inspector admin authentication via Bearer header or cookie."""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request
from starlette.responses import Response

__all__ = ["issue_inspector_cookie", "require_inspector_token"]

_COOKIE_NAME = "arthor_inspector_token"


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth is None:
        return None
    prefix = "Bearer "
    if not auth.startswith(prefix):
        return None
    return auth[len(prefix) :].strip() or None


def _const_time_str_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


async def require_inspector_token(request: Request) -> None:
    services = getattr(request.app.state, "services", None)
    settings = getattr(services, "settings", None) if services else None
    expected = getattr(settings, "inspector_admin_token", None)

    if expected is None:
        raise HTTPException(status_code=503, detail="inspector_admin_token_unset")

    bearer = _extract_bearer(request)
    cookie = request.cookies.get(_COOKIE_NAME)

    if bearer is not None and _const_time_str_equal(bearer, expected):
        return
    if cookie is not None and _const_time_str_equal(cookie, expected):
        return

    raise HTTPException(status_code=401, detail="unauthorized")


def issue_inspector_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        _COOKIE_NAME,
        token,
        max_age=86400,
        httponly=True,
        secure=True,
        samesite="strict",
    )
