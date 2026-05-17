"""s09 AC-5: batch failure raises ProviderError; the orchestrator-level fallback is s10's concern."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from _fake_genai import FakeGenAIClient


@dataclass
class FakeStyleProfile:
    id: str = "sp-1"
    register: str = "photographic"


@dataclass
class FakeSlotPrompt:
    text: str
    prompt_hash: str
    prompt_template_version: str = "1.0"
    dimensions: tuple[int, int] = (1024, 1024)


@pytest.mark.asyncio
async def test_pack_consistent_batch_failure_raises_provider_error():
    try:
        from app.providers.google_nano_banana import GoogleNanoBananaProvider  # type: ignore[import-not-found]
        from app.providers.openai_image import ProviderError  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: providers must be importable ({exc})")

    fake = FakeGenAIClient(raise_exc=RuntimeError("simulated batch failure"))
    provider = GoogleNanoBananaProvider(client=fake)

    with pytest.raises(ProviderError):
        await provider.generate_pack_consistent(
            prompts=[FakeSlotPrompt(text="x", prompt_hash="h")],
            style_profile=FakeStyleProfile(),
            seed=1,
        )
