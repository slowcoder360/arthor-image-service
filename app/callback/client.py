"""HMAC-signed completion callbacks (ADR-0006)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from app.auth.sign import sign_outbound

logger = logging.getLogger(__name__)


async def send_completion_callback(
    *,
    callback_url: str,
    body: dict[str, Any],
    secret: str,
    client_factory: Callable[..., Any],
) -> None:
    payload = json.dumps(body, sort_keys=True).encode("utf-8")
    headers = sign_outbound(secret, payload)
    async with client_factory() as client:
        resp = await client.post(callback_url, content=payload, headers=dict(headers))
    if resp.status_code < 200 or resp.status_code >= 300:
        logger.warning(
            "completion callback HTTP %s for %s (body keys=%s)",
            resp.status_code,
            callback_url,
            tuple(sorted(body.keys())),
        )


__all__ = ["send_completion_callback"]
