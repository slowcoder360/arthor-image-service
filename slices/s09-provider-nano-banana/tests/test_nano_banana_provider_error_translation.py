"""s09 AC-8: SDK error translates to ProviderError."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from _fake_genai import FakeGenAIClient


@dataclass
class FakeStyleProfile:
    id: str = "sp-1"
    register: str = "photographic"


@pytest.mark.asyncio
async def test_sdk_error_translates_to_provider_error():
    try:
        from app.providers.google_nano_banana import GoogleNanoBananaProvider  # type: ignore[import-not-found]
        from app.providers.openai_image import ProviderError  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-8: providers must be importable ({exc})")

    fake = FakeGenAIClient(raise_exc=RuntimeError("simulated google.genai.errors.APIError"))
    provider = GoogleNanoBananaProvider(client=fake)

    with pytest.raises(ProviderError):
        await provider.generate_single(
            prompt="x",
            dimensions=(1024, 1024),
            seed=1,
            style_profile=FakeStyleProfile(),
            reference_images=None,
        )
