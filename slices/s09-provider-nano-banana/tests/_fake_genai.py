"""Fake google.genai-shaped client for s09 provider tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _FakeImage:
    image_bytes: bytes
    seed: int | None = None


class FakeGenAIClient:
    def __init__(
        self,
        single_response: list[bytes] | None = None,
        batch_response: list[bytes] | None = None,
        single_seed: int | None = None,
        raise_exc: BaseException | None = None,
    ):
        self._single_response = single_response or [b"\x89PNGfake-single"]
        self._batch_response = batch_response or [b"\x89PNGbatch-1", b"\x89PNGbatch-2"]
        self._single_seed = single_seed
        self._raise_exc = raise_exc
        self.single_calls: list[dict[str, Any]] = []
        self.batch_calls: list[dict[str, Any]] = []

    async def generate_image(self, **kwargs):
        self.single_calls.append(kwargs)
        if self._raise_exc is not None:
            raise self._raise_exc
        return [
            _FakeImage(image_bytes=b, seed=self._single_seed)
            for b in self._single_response
        ]

    async def generate_images_batch(self, **kwargs):
        self.batch_calls.append(kwargs)
        if self._raise_exc is not None:
            raise self._raise_exc
        return [_FakeImage(image_bytes=b) for b in self._batch_response]
