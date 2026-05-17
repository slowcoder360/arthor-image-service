"""s09 AC-7: PROVIDERS registry contains both providers; get_provider() routes by name."""

from __future__ import annotations

import pytest


def test_providers_registry_has_both_entries():
    try:
        from app.providers import PROVIDERS  # type: ignore[import-not-found]
        from app.providers.google_nano_banana import GoogleNanoBananaProvider  # type: ignore[import-not-found]
        from app.providers.openai_image import OpenAIImageProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-7: PROVIDERS registry must be importable ({exc})")

    assert "openai_image" in PROVIDERS, (
        "AC-7: PROVIDERS must include 'openai_image' key"
    )
    assert "google_nano_banana" in PROVIDERS, (
        "AC-7: PROVIDERS must include 'google_nano_banana' key"
    )
    assert PROVIDERS["openai_image"] is OpenAIImageProvider, (
        "AC-7: PROVIDERS['openai_image'] must be OpenAIImageProvider class"
    )
    assert PROVIDERS["google_nano_banana"] is GoogleNanoBananaProvider, (
        "AC-7: PROVIDERS['google_nano_banana'] must be GoogleNanoBananaProvider class"
    )


def test_get_provider_routes_by_name():
    try:
        from app.config import Settings  # type: ignore[import-not-found]
        from app.providers import get_provider  # type: ignore[import-not-found]
        from app.providers.google_nano_banana import GoogleNanoBananaProvider  # type: ignore[import-not-found]
        from app.providers.openai_image import OpenAIImageProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-7: get_provider must be importable ({exc})")

    settings = Settings()
    openai_provider = get_provider("openai_image", settings)
    assert isinstance(openai_provider, OpenAIImageProvider), (
        "AC-7: get_provider('openai_image', settings) must return an OpenAIImageProvider"
    )
    google_provider = get_provider("google_nano_banana", settings)
    assert isinstance(google_provider, GoogleNanoBananaProvider), (
        "AC-7: get_provider('google_nano_banana', settings) must return a GoogleNanoBananaProvider"
    )


def test_get_provider_unknown_raises_key_error():
    try:
        from app.config import Settings  # type: ignore[import-not-found]
        from app.providers import get_provider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-7: get_provider must be importable ({exc})")

    with pytest.raises(KeyError):
        get_provider("not-a-real-provider", Settings())
