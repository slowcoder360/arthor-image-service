"""Shared image-provider types (ADR 0007)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class ProviderResult:
    image_bytes: bytes
    width: int
    height: int
    seed: int | None
    provider: str
    model_version: str
    cost_cents: int
    latency_ms: int
    external_id: str | None
    response_shape: dict
    determinism_level: str


@runtime_checkable
class ImageProvider(Protocol):
    name: str
    supports_pack_consistent: bool
    supports_reference_image: bool

    async def generate_single(
        self,
        *,
        prompt: str,
        dimensions: tuple[int, int],
        seed: int | None,
        style_profile: Any,
        reference_images: list[bytes] | None = None,
    ) -> ProviderResult: ...

    async def generate_pack_consistent(
        self,
        *,
        prompts: list[Any],
        style_profile: Any,
        seed: int | None,
    ) -> list[ProviderResult]: ...
