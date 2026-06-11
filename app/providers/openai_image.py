"""OpenAI Images API-backed ImageProvider."""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import Any, ClassVar

import openai

from app.providers.protocol import ProviderResult

logger = logging.getLogger(__name__)

# Default model pinned at build time; override via OPENAI_IMAGE_MODEL env.
DEFAULT_MODEL_VERSION = "gpt-image-2"


class ProviderError(Exception):
    """Unified failure type for callers (SDK errors translated here)."""


class UnknownModelVersion(Exception):
    """Raised when the cost table has no rates for ``model_version``."""


class OpenAICostTable:
    """Per-model, per-output-size marginal cost in USD cents.

    Sources: OpenAI GPT Image pricing (medium tier, May 2025 snapshot).
    Bump ``RATES`` via one-line edits.
    """

    RATES: ClassVar[dict[str, dict[tuple[int, int], int]]] = {
        DEFAULT_MODEL_VERSION: {
            (1024, 1024): 4,
            (1024, 1536): 6,
            (1536, 1024): 6,
            (1536, 1536): 8,
            (1920, 1080): 8,
        },
        "gpt-image-1.5": {
            (1024, 1024): 4,
            (1024, 1536): 5,
            (1536, 1024): 5,
            (1536, 1536): 8,
            (1920, 1080): 8,
        },
        "gpt-image-2": {
            (1024, 1024): 5,
            (1024, 1536): 6,
            (1536, 1024): 6,
            (1536, 1536): 10,
            (1920, 1080): 10,
        },
    }

    @classmethod
    def cost_for(cls, model_version: str, dimensions: tuple[int, int]) -> int:
        dims = dimensions
        table = cls.RATES.get(model_version)
        if table is None:
            raise UnknownModelVersion(model_version)
        if dims not in table:
            raise UnknownModelVersion(f"{model_version}@{dims[0]}x{dims[1]}")
        return table[dims]


def _latency_ms_since(t0: float) -> int:
    return max(1, int((time.perf_counter() - t0) * 1000))


def _response_trim(resp: object, dims: tuple[int, int]) -> dict:
    """Trimmed structured fields for persistence (ADR 0007)."""
    model = getattr(resp, "model", None)
    created = getattr(resp, "created", None)
    w, h = dims
    return {
        "model": model,
        "created": created,
        "size": f"{w}x{h}",
        "n": 1,
        "b64_present": True,
    }


def _b64decode_first_image(resp: object) -> tuple[bytes, str | None]:
    data = getattr(resp, "data", None)
    if not data:
        raise ProviderError("OpenAI images response contained no images")
    first = data[0]
    b64 = getattr(first, "b64_json", None)
    if not isinstance(b64, str) or not b64:
        raise ProviderError("OpenAI images response missing b64_json")
    image_bytes = base64.b64decode(b64)
    ext_id = getattr(first, "revised_prompt", None)
    external_id = str(ext_id) if ext_id is not None else None
    return image_bytes, external_id


class OpenAIImageProvider:
    name = "openai_image"
    supports_pack_consistent = False
    supports_reference_image = True

    def __init__(
        self,
        client: openai.AsyncOpenAI,
        model_version: str | None = None,
        *,
        quality: str = "medium",
    ) -> None:
        self._client = client
        self.model_version = model_version if model_version is not None else DEFAULT_MODEL_VERSION
        self._quality = quality

    async def generate_single(
        self,
        *,
        prompt: str,
        dimensions: tuple[int, int],
        seed: int | None,
        style_profile: Any,
        reference_images: list[bytes] | None = None,
    ) -> ProviderResult:
        _ = seed
        _ = style_profile

        if seed is not None:
            logger.debug("OpenAI Images API ignores user seeds; omitting determinism coupling")

        w, h = dimensions
        cost_cents = OpenAICostTable.cost_for(self.model_version, dimensions)
        t0 = time.perf_counter()
        trimmed: dict
        external_id: str | None

        try:
            if reference_images:
                source = io.BytesIO(reference_images[0])
                source.name = "reference.png"
                resp = await self._client.images.edit(
                    model=self.model_version,
                    prompt=prompt,
                    image=source,
                    size=f"{w}x{h}",
                )
                trimmed = _response_trim(resp, dimensions)
                if len(reference_images) > 1:
                    trimmed["reference_warning"] = "multiple_reference_images_using_first_only"
            else:
                gen_kwargs: dict[str, Any] = {
                    "model": self.model_version,
                    "prompt": prompt,
                    "size": f"{w}x{h}",
                }
                if self._quality:
                    gen_kwargs["quality"] = self._quality
                resp = await self._client.images.generate(**gen_kwargs)
                trimmed = _response_trim(resp, dimensions)

            latency_ms = _latency_ms_since(t0)
            image_bytes, ext_from_datum = _b64decode_first_image(resp)
            rid = getattr(resp, "id", None)
            external_id = str(rid) if rid is not None else ext_from_datum

            return ProviderResult(
                image_bytes=image_bytes,
                width=w,
                height=h,
                seed=None,
                provider=self.name,
                model_version=self.model_version,
                cost_cents=cost_cents,
                latency_ms=latency_ms,
                external_id=external_id,
                response_shape=trimmed,
                determinism_level="best-effort",
            )

        except openai.APIError as exc:
            msg = getattr(exc, "message", None) or str(exc) or repr(exc)
            raise ProviderError(msg) from exc

    async def generate_pack_consistent(
        self,
        *,
        prompts: list[Any],
        style_profile: Any,
        seed: int | None,
    ) -> list[ProviderResult]:
        _ = prompts
        _ = style_profile
        _ = seed
        raise NotImplementedError(
            "OpenAI image API does not support native pack-consistent generation; "
            "the orchestrator falls back to per-slot calls with reference conditioning"
        )
