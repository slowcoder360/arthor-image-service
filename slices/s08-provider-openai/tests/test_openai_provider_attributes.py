"""s08 AC-3: OpenAIImageProvider class attributes."""

from __future__ import annotations

import pytest

from _fake_openai import FakeAsyncOpenAI


def test_openai_provider_class_attributes():
    try:
        from app.providers.openai_image import OpenAIImageProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: OpenAIImageProvider must be importable ({exc})")

    provider = OpenAIImageProvider(client=FakeAsyncOpenAI())
    assert provider.name == "openai_image", (
        f"AC-3: OpenAIImageProvider.name must equal 'openai_image'; got {provider.name!r}"
    )
    assert provider.supports_pack_consistent is False, (
        "AC-3: OpenAIImageProvider.supports_pack_consistent must be False"
    )
    assert provider.supports_reference_image is True, (
        "AC-3: OpenAIImageProvider.supports_reference_image must be True"
    )
    assert isinstance(provider.model_version, str) and provider.model_version, (
        "AC-3: OpenAIImageProvider.model_version must be a non-empty string set at construction"
    )
