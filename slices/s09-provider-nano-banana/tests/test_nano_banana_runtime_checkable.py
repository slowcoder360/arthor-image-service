"""s09 AC-1: nano-banana provider satisfies the ImageProvider Protocol via isinstance."""

from __future__ import annotations

import pytest

from _fake_genai import FakeGenAIClient


def test_nano_banana_satisfies_image_provider_protocol():
    try:
        from app.providers.google_nano_banana import GoogleNanoBananaProvider  # type: ignore[import-not-found]
        from app.providers.protocol import ImageProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: providers must be importable ({exc})")

    provider = GoogleNanoBananaProvider(client=FakeGenAIClient())
    assert isinstance(provider, ImageProvider), (
        "AC-1: GoogleNanoBananaProvider must satisfy isinstance(provider, ImageProvider)"
    )
