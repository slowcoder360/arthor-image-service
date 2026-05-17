"""Fake openai.AsyncOpenAI-shaped client for s08 provider tests."""

from __future__ import annotations

import base64
from typing import Any


class FakeImagesAPI:
    def __init__(self, generate_response=None, edit_response=None, raise_exc=None):
        self._generate_response = generate_response
        self._edit_response = edit_response
        self._raise_exc = raise_exc
        self.generate_calls: list[dict[str, Any]] = []
        self.edit_calls: list[dict[str, Any]] = []

    async def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._generate_response

    async def edit(self, **kwargs):
        self.edit_calls.append(kwargs)
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._edit_response


class FakeAsyncOpenAI:
    def __init__(
        self,
        generate_response=None,
        edit_response=None,
        raise_exc=None,
    ):
        self.images = FakeImagesAPI(
            generate_response=generate_response,
            edit_response=edit_response,
            raise_exc=raise_exc,
        )


def b64_png_bytes() -> str:
    return base64.b64encode(b"\x89PNG\r\n\x1a\nfake-bytes-here").decode()


def make_generate_response(model: str = "gpt-image-1", b64: str | None = None):
    """Mimic the shape of openai.images.generate response."""

    class _Datum:
        def __init__(self, b64: str):
            self.b64_json = b64

    class _Resp:
        def __init__(self, model_id: str, b64: str):
            self.model = model_id
            self.created = 1700000000
            self.data = [_Datum(b64)]

    return _Resp(model, b64 or b64_png_bytes())
