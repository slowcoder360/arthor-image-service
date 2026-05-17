"""s08 AC-2: ImageProvider Protocol is @runtime_checkable; OpenAIImageProvider passes isinstance."""

from __future__ import annotations

import pytest

from _fake_openai import FakeAsyncOpenAI


def test_isinstance_against_runtime_checkable_protocol():
    try:
        from app.providers.openai_image import OpenAIImageProvider  # type: ignore[import-not-found]
        from app.providers.protocol import ImageProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: providers must be importable ({exc})")

    provider = OpenAIImageProvider(client=FakeAsyncOpenAI())
    assert isinstance(provider, ImageProvider), (
        "AC-2: OpenAIImageProvider must satisfy isinstance(provider, ImageProvider) — Protocol must be @runtime_checkable"
    )


def test_non_provider_does_not_satisfy_protocol():
    try:
        from app.providers.protocol import ImageProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: ImageProvider must be importable ({exc})")

    class NotAProvider:
        pass

    assert not isinstance(NotAProvider(), ImageProvider), (
        "AC-2: an obvious non-provider must NOT satisfy isinstance(_, ImageProvider)"
    )
