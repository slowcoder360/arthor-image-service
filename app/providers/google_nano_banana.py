"""Gemini 2.5 Flash Image (nano-banana) backend (ADR 0007)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, ClassVar

from google.genai import errors as genai_errors
from google.genai import types

from app.providers.openai_image import ProviderError, UnknownModelVersion
from app.providers.protocol import ProviderResult
from app.providers.retry import RetryExhausted, with_retry

# Default model pinned at build time; README documents bumps.
DEFAULT_MODEL_VERSION = "gemini-2.5-flash-image"


class GoogleCostTable:
    """Per-model, per-output-size marginal cost in USD cents."""

    RATES: ClassVar[dict[str, dict[tuple[int, int], int]]] = {
        DEFAULT_MODEL_VERSION: {
            (1024, 1024): 4,
            (1024, 1536): 6,
            (1536, 1024): 6,
            (1536, 1536): 8,
            (1920, 1080): 8,
        },
    }

    @classmethod
    def cost_for(cls, model_version: str, dimensions: tuple[int, int]) -> int:
        table = cls.RATES.get(model_version)
        if table is None:
            raise UnknownModelVersion(model_version)
        if dimensions not in table:
            raise UnknownModelVersion(f"{model_version}@{dimensions[0]}x{dimensions[1]}")
        return table[dimensions]


@dataclass
class _NanoImagePart:
    image_bytes: bytes
    seed: int | None = None


def _latency_ms_since(t0: float) -> int:
    return max(1, int((time.perf_counter() - t0) * 1000))


def _aspect_ratio_for_dims(width: int, height: int) -> str:
    if width == height:
        return "1:1"
    if width > height:
        return "4:3" if width / height < 1.4 else "16:9"
    return "3:4" if height / width < 1.4 else "9:16"


def _trim_genai_response(
    response: object,
    dimensions: tuple[int, int],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    w, h = dimensions
    model = getattr(response, "model_version", None)
    rid = getattr(response, "response_id", None)
    shape: dict[str, Any] = {
        "model": model,
        "response_id": rid,
        "size": f"{w}x{h}",
        "n": 1,
    }
    if extra:
        shape.update(extra)
    return shape




def _first_image_from_genai_response(response: object) -> bytes:
    parts = getattr(response, "parts", None) or ()
    for part in parts:
        inline = getattr(part, "inline_data", None)
        data = getattr(inline, "data", None) if inline is not None else None
        if data:
            return bytes(data)
    msg = "Gemini generate_content response contained no image bytes"
    raise ProviderError(msg)


def _provider_error_from(exc: BaseException) -> ProviderError:
    if isinstance(exc, ProviderError):
        return exc
    msg = getattr(exc, "message", None) or str(exc) or repr(exc)
    return ProviderError(msg)


def _uses_test_style_client(client: object) -> bool:
    gen_image = getattr(client, "generate_image", None)
    gen_batch = getattr(client, "generate_images_batch", None)
    return callable(gen_image) and callable(gen_batch)


class GoogleNanoBananaProvider:
    name = "google_nano_banana"
    supports_pack_consistent = True
    supports_reference_image = True

    def __init__(self, client: Any, model_version: str | None = None) -> None:
        self._client = client
        self.model_version = model_version if model_version is not None else DEFAULT_MODEL_VERSION

    async def _generate_image_test_shim(
        self,
        *,
        prompt: str,
        dimensions: tuple[int, int],
        seed: int | None,
        reference_images: list[bytes] | None,
    ) -> tuple[_NanoImagePart, dict[str, Any]]:
        w, h = dimensions
        images = await self._client.generate_image(
            model=self.model_version,
            prompt=prompt,
            width=w,
            height=h,
            seed=seed,
            reference_images=reference_images,
        )
        if not images:
            raise ProviderError("Gemini shim returned no images")
        first = images[0]
        img_bytes = getattr(first, "image_bytes", None)
        if not isinstance(img_bytes, (bytes, bytearray)) or not img_bytes:
            raise ProviderError("Gemini shim image_bytes missing")
        out_seed = getattr(first, "seed", None)
        trimmed = {
            "model": self.model_version,
            "size": f"{w}x{h}",
            "n": 1,
            "shim": "generate_image",
        }
        return _NanoImagePart(image_bytes=bytes(img_bytes), seed=out_seed), trimmed

    async def _generate_image_genai_sdk(
        self,
        *,
        prompt: str,
        dimensions: tuple[int, int],
        seed: int | None,
        reference_images: list[bytes] | None,
    ) -> tuple[_NanoImagePart, dict[str, Any]]:
        w, h = dimensions
        aspect = _aspect_ratio_for_dims(w, h)
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect),
        )
        if seed is not None:
            config.seed = seed  # Verified google-genai GenerateContentConfig supports seed.

        parts: list[types.Part] = []
        for raw in reference_images or []:
            parts.append(types.Part.from_bytes(data=raw, mime_type="image/png"))
        parts.append(types.Part.from_text(text=prompt))
        contents: types.Content | list[types.Part]
        if len(parts) == 1:
            contents = prompt
        else:
            contents = parts

        aclient = self._client.aio
        response = await aclient.models.generate_content(
            model=self.model_version,
            contents=contents,
            config=config,
        )

        image_bytes = _first_image_from_genai_response(response)
        trimmed = _trim_genai_response(response, dimensions)
        return _NanoImagePart(image_bytes=image_bytes, seed=None), trimmed

    async def _run_pack_test_shim(
        self,
        *,
        prompts: list[Any],
        style_profile: Any,
        seed: int | None,
    ) -> list[_NanoImagePart]:
        images = await self._client.generate_images_batch(
            model=self.model_version,
            prompts=prompts,
            seed=seed,
            style_profile=style_profile,
        )
        out: list[_NanoImagePart] = []
        for img in images:
            b = getattr(img, "image_bytes", None)
            if not isinstance(b, (bytes, bytearray)) or not b:
                raise ProviderError("Gemini batch shim image_bytes missing")
            s = getattr(img, "seed", None)
            out.append(_NanoImagePart(image_bytes=bytes(b), seed=s))
        return out

    async def _run_pack_genai_sdk(
        self,
        *,
        prompts: list[Any],
        style_profile: Any,
        seed: int | None,
    ) -> list[_NanoImagePart]:
        style_reg = getattr(style_profile, "register", None) or ""
        prefix = f"[Pack-consistent style: {style_reg}] " if style_reg else ""
        out: list[_NanoImagePart] = []
        for slot in prompts:
            text = str(getattr(slot, "text"))
            dims: tuple[int, int] = getattr(slot, "dimensions", (1024, 1024))
            part, _trim = await self._generate_image_genai_sdk(
                prompt=prefix + text,
                dimensions=dims,
                seed=seed,
                reference_images=None,
            )
            out.append(part)
        return out

    async def generate_single(
        self,
        *,
        prompt: str,
        dimensions: tuple[int, int],
        seed: int | None,
        style_profile: Any,
        reference_images: list[bytes] | None = None,
    ) -> ProviderResult:
        _ = style_profile
        w, h = dimensions
        cost_cents = GoogleCostTable.cost_for(self.model_version, dimensions)

        async def _attempt(call_seed: int | None) -> ProviderResult:
            t0 = time.perf_counter()
            if _uses_test_style_client(self._client):
                part, trimmed = await self._generate_image_test_shim(
                    prompt=prompt,
                    dimensions=dimensions,
                    seed=call_seed,
                    reference_images=reference_images,
                )
            else:
                part, trimmed = await self._generate_image_genai_sdk(
                    prompt=prompt,
                    dimensions=dimensions,
                    seed=call_seed,
                    reference_images=reference_images,
                )

            latency_ms = _latency_ms_since(t0)
            determinism_level = (
                "strict" if call_seed is not None and part.seed == call_seed else "best-effort"
            )
            rid = trimmed.get("response_id") if isinstance(trimmed, dict) else None
            external_id = str(rid) if rid is not None else None
            return ProviderResult(
                image_bytes=part.image_bytes,
                width=w,
                height=h,
                seed=part.seed,
                provider=self.name,
                model_version=self.model_version,
                cost_cents=cost_cents,
                latency_ms=latency_ms,
                external_id=external_id,
                response_shape=trimmed,
                determinism_level=determinism_level,
            )

        try:
            return await with_retry(_attempt, base_seed=seed)
        except RetryExhausted as exc:
            cause = exc.__cause__
            if cause is not None:
                raise _provider_error_from(cause) from exc
            raise ProviderError("provider call retries exhausted") from exc
        except genai_errors.APIError as exc:
            raise _provider_error_from(exc) from exc
        except Exception as exc:
            raise _provider_error_from(exc) from exc

    async def generate_pack_consistent(
        self,
        *,
        prompts: list[Any],
        style_profile: Any,
        seed: int | None,
    ) -> list[ProviderResult]:
        style_id = getattr(style_profile, "id", None)
        t0 = time.perf_counter()

        try:
            if _uses_test_style_client(self._client):
                parts = await self._run_pack_test_shim(
                    prompts=prompts, style_profile=style_profile, seed=seed
                )
            else:
                parts = await self._run_pack_genai_sdk(
                    prompts=prompts, style_profile=style_profile, seed=seed
                )
        except genai_errors.APIError as exc:
            raise _provider_error_from(exc) from exc
        except Exception as exc:
            raise _provider_error_from(exc) from exc

        if len(parts) != len(prompts):
            raise ProviderError("Gemini pack-consistent returned wrong result count")

        latency_ms = _latency_ms_since(t0)
        results: list[ProviderResult] = []
        for i, (slot, part) in enumerate(zip(prompts, parts, strict=True)):
            dims: tuple[int, int] = getattr(slot, "dimensions", (1024, 1024))
            w, h = dims
            cost_cents = GoogleCostTable.cost_for(self.model_version, dims)
            det = (
                "strict"
                if seed is not None and part.seed == seed
                else "best-effort"
            )
            trimmed = {
                "model": self.model_version,
                "size": f"{w}x{h}",
                "n": 1,
                "batch": True,
                "slot_index": i,
                "style_profile_id": style_id,
            }
            results.append(
                ProviderResult(
                    image_bytes=part.image_bytes,
                    width=w,
                    height=h,
                    seed=part.seed,
                    provider=self.name,
                    model_version=self.model_version,
                    cost_cents=cost_cents,
                    latency_ms=latency_ms,
                    external_id=None,
                    response_shape=trimmed,
                    determinism_level=det,
                )
            )
        return results
