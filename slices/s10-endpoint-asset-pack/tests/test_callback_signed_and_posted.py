"""s10 AC-13: send_completion_callback signs body with X-Arthor-Signature; body shape matches schema."""

from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_send_completion_callback_signs_and_posts():
    try:
        from app.auth.hmac import verify_signature  # type: ignore[import-not-found]
        from app.callback.client import send_completion_callback  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-13: callback + verify_signature must be importable ({exc})")

    posts: list[dict] = []

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, content=None, headers=None, **kwargs):
            posts.append({"url": url, "content": content, "headers": headers})

            class _Resp:
                status_code = 204

                def raise_for_status(self):
                    return None

            return _Resp()

    body = {
        "agent_run_id": "abc",
        "site_id": "xyz",
        "status": "complete",
        "assets": [],
        "total_cost_cents": 23,
        "duration_seconds": 1.5,
    }
    secret = "k"

    await send_completion_callback(
        callback_url="https://x.example/cb",
        body=body,
        secret=secret,
        client_factory=lambda: FakeAsyncClient(),
    )

    assert posts, "AC-13: callback must POST to the URL"
    last = posts[-1]
    sig_header = (last.get("headers") or {}).get("X-Arthor-Signature")
    assert sig_header, "AC-13: POST headers must include 'X-Arthor-Signature'"
    raw = (
        last.get("content") if isinstance(last.get("content"), (bytes, bytearray)) else json.dumps(body, sort_keys=True).encode()
    )
    assert verify_signature(secret, raw, sig_header) is True, (
        "AC-13: outbound signature must verify under verify_signature with the same secret"
    )

    parsed = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
    for required in (
        "agent_run_id",
        "site_id",
        "status",
        "assets",
        "total_cost_cents",
        "duration_seconds",
    ):
        assert required in parsed, (
            f"AC-13: callback body must include '{required}' field"
        )
