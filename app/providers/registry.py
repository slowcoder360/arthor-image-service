"""Provider factory — separate module so tests can monkeypatch ``get_provider``."""

from __future__ import annotations

import openai
from google import genai

from app.config import Settings
from app.providers.google_nano_banana import GoogleNanoBananaProvider
from app.providers.openai_image import OpenAIImageProvider
from app.providers.protocol import ImageProvider

PROVIDERS: dict[str, type[ImageProvider]] = {
    OpenAIImageProvider.name: OpenAIImageProvider,
    GoogleNanoBananaProvider.name: GoogleNanoBananaProvider,
}


def get_provider(name: str, settings: Settings) -> ImageProvider:
    cls = PROVIDERS[name]
    if cls is OpenAIImageProvider:
        api_key = settings.openai_api_key or "unset-openai-key"
        return OpenAIImageProvider(
            client=openai.AsyncOpenAI(api_key=api_key),
            model_version=settings.openai_image_model,
            quality=settings.openai_image_quality,
        )
    if cls is GoogleNanoBananaProvider:
        api_key = settings.google_api_key or "unset-google-key"
        return GoogleNanoBananaProvider(
            client=genai.Client(api_key=api_key),
            model_version=settings.google_image_model,
        )
    raise RuntimeError(f"get_provider: unhandled class {cls!r} for {name!r}")
