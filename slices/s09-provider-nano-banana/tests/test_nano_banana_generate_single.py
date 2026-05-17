"""s09 AC-2: generate_single returns ProviderResult with valid determinism_level + latency."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from _fake_genai import FakeGenAIClient


@dataclass
class FakeStyleProfile:
    id: str = "sp-1"
    register: str = "photographic"


@pytest.mark.asyncio
async def test_generate_single_returns_provider_result():
    try:
        from app.providers.google_nano_banana import GoogleNanoBananaProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: GoogleNanoBananaProvider must be importable ({exc})")

    fake = FakeGenAIClient(single_seed=99)
    provider = GoogleNanoBananaProvider(client=fake)
    result = await provider.generate_single(
        prompt="a serene workspace",
        dimensions=(1024, 1024),
        seed=99,
        style_profile=FakeStyleProfile(),
        reference_images=None,
    )
    assert result.determinism_level in {"strict", "best-effort"}, (
        f"AC-2: determinism_level must be 'strict' or 'best-effort'; got {result.determinism_level!r}"
    )
    assert result.latency_ms > 0, "AC-2: latency_ms must be positive"
    assert result.provider == "google_nano_banana", (
        "AC-2: provider must equal 'google_nano_banana'"
    )
    assert isinstance(result.image_bytes, (bytes, bytearray)) and result.image_bytes, (
        "AC-2: image_bytes must be non-empty bytes"
    )
