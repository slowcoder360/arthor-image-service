"""Repository-root pytest hooks visible to suites under ``slices/`` (ancestor conftest chain)."""

from __future__ import annotations

import httpx
import pytest


def pytest_configure(config: pytest.Config) -> None:  # noqa: ARG001
    """Hook: relax ``openai.APIError`` ctor for slice tests built against older call shapes."""
    try:
        import openai as _openai
    except ImportError:
        return

    _real_init = _openai.APIError.__init__

    def _api_error_compat(
        self: object,
        message: str,
        request: httpx.Request | None = None,
        *,
        body: object | None = None,
    ) -> None:
        if request is None:
            request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
        _real_init(self, message, request, body=body)

    _openai.APIError.__init__ = _api_error_compat  # type: ignore[method-assign]
