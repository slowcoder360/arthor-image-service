"""Image backends (ADR 0007)."""

from __future__ import annotations

from app.providers.google_nano_banana import GoogleNanoBananaProvider, GoogleCostTable
from app.providers.openai_image import (
    DEFAULT_MODEL_VERSION,
    OpenAICostTable,
    OpenAIImageProvider,
    ProviderError,
    UnknownModelVersion,
)
from app.providers.protocol import ImageProvider, ProviderResult
from app.providers.registry import PROVIDERS, get_provider
from app.providers.retry import RetryExhausted, with_retry

PROVIDER_REGISTRY: dict[str, type[OpenAIImageProvider]] = {
    OpenAIImageProvider.name: OpenAIImageProvider,
}

__all__ = (
    "DEFAULT_MODEL_VERSION",
    "GoogleCostTable",
    "GoogleNanoBananaProvider",
    "ImageProvider",
    "OpenAICostTable",
    "OpenAIImageProvider",
    "PROVIDER_REGISTRY",
    "PROVIDERS",
    "ProviderError",
    "ProviderResult",
    "RetryExhausted",
    "UnknownModelVersion",
    "get_provider",
    "with_retry",
)
