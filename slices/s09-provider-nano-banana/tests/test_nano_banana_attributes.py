"""s09 AC-1: GoogleNanoBananaProvider class attributes."""

from __future__ import annotations

import pytest

from _fake_genai import FakeGenAIClient


def test_nano_banana_class_attributes():
    try:
        from app.providers.google_nano_banana import GoogleNanoBananaProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: GoogleNanoBananaProvider must be importable ({exc})")

    provider = GoogleNanoBananaProvider(client=FakeGenAIClient())
    assert provider.name == "google_nano_banana", (
        f"AC-1: name must equal 'google_nano_banana'; got {provider.name!r}"
    )
    assert provider.supports_pack_consistent is True, (
        "AC-1: supports_pack_consistent must be True for nano-banana"
    )
    assert provider.supports_reference_image is True, (
        "AC-1: supports_reference_image must be True for nano-banana"
    )
    assert isinstance(provider.model_version, str) and provider.model_version, (
        "AC-1: model_version must be a non-empty string"
    )
