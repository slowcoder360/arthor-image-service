"""s08 AC-8: openai.APIError raised by client is translated into ProviderError."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from _fake_openai import FakeAsyncOpenAI


@dataclass
class FakeStyleProfile:
    id: str = "sp-1"
    register: str = "photographic"


@pytest.mark.asyncio
async def test_openai_api_error_translates_to_provider_error():
    try:
        import openai
    except ImportError as exc:
        pytest.skip(f"openai SDK not installed in this environment ({exc})")
    try:
        from app.providers.openai_image import (  # type: ignore[import-not-found]
            OpenAIImageProvider,
            ProviderError,
        )
    except ImportError as exc:
        pytest.fail(
            f"AC-8: OpenAIImageProvider / ProviderError must be importable ({exc})"
        )

    api_error = getattr(openai, "APIError", Exception)("simulated SDK failure")
    fake = FakeAsyncOpenAI(raise_exc=api_error)
    provider = OpenAIImageProvider(client=fake)

    with pytest.raises(ProviderError):
        await provider.generate_single(
            prompt="x",
            dimensions=(1024, 1024),
            seed=1,
            style_profile=FakeStyleProfile(),
            reference_images=None,
        )
