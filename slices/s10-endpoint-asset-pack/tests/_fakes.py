"""Shared fake-provider, fake-pool, fake-r2, fake-callback fixtures for s10 worker tests."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeCall:
    method: str
    slot_id: str | None
    seed: int | None
    has_reference: bool
    prompt: str | None = None


class FakeProvider:
    """Records every method call with slot_id when provided."""

    def __init__(
        self,
        name: str = "openai_image",
        supports_pack_consistent: bool = False,
        supports_reference_image: bool = True,
        model_version: str = "gpt-image-1",
        single_failures: int = 0,
        pack_failure: bool = False,
    ):
        self.name = name
        self.supports_pack_consistent = supports_pack_consistent
        self.supports_reference_image = supports_reference_image
        self.model_version = model_version
        self.calls: list[FakeCall] = []
        self._single_failures_remaining = single_failures
        self._pack_failure = pack_failure

    async def generate_single(self, **kwargs):
        slot_id = kwargs.get("slot_id")
        seed = kwargs.get("seed")
        ref = kwargs.get("reference_images") or []
        self.calls.append(
            FakeCall(
                method="generate_single",
                slot_id=slot_id,
                seed=seed,
                has_reference=bool(ref),
                prompt=str(kwargs.get("prompt", ""))[:60],
            )
        )
        if self._single_failures_remaining > 0:
            self._single_failures_remaining -= 1
            try:
                from app.providers.openai_image import ProviderError  # type: ignore[import-not-found]
            except Exception:  # noqa: BLE001
                ProviderError = RuntimeError
            raise ProviderError(f"fake failure for slot={slot_id}")
        return _make_provider_result(self.name, self.model_version)

    async def generate_pack_consistent(self, **kwargs):
        prompts = kwargs.get("prompts") or []
        self.calls.append(
            FakeCall(
                method="generate_pack_consistent",
                slot_id=None,
                seed=kwargs.get("seed"),
                has_reference=False,
                prompt=f"batch:n={len(prompts)}",
            )
        )
        if self._pack_failure:
            try:
                from app.providers.openai_image import ProviderError  # type: ignore[import-not-found]
            except Exception:  # noqa: BLE001
                ProviderError = RuntimeError
            raise ProviderError("fake batch failure")
        return [_make_provider_result(self.name, self.model_version) for _ in prompts]


def _make_provider_result(provider: str, model_version: str):
    try:
        from app.providers.protocol import ProviderResult  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return {
            "image_bytes": b"\x89PNGfake",
            "width": 1024,
            "height": 1024,
            "seed": None,
            "provider": provider,
            "model_version": model_version,
            "cost_cents": 1,
            "latency_ms": 1,
            "external_id": "x",
            "response_shape": {},
            "determinism_level": "best-effort",
        }
    return ProviderResult(
        image_bytes=b"\x89PNGfake",
        width=1024,
        height=1024,
        seed=None,
        provider=provider,
        model_version=model_version,
        cost_cents=1,
        latency_ms=1,
        external_id="x",
        response_shape={},
        determinism_level="best-effort",
    )


class FakeCallbackClient:
    def __init__(self):
        self.posts: list[dict[str, Any]] = []

    async def send_completion_callback(self, callback_url: str, body: dict, *, secret: str = "k"):
        self.posts.append(
            {"url": callback_url, "body": body, "secret": secret}
        )
