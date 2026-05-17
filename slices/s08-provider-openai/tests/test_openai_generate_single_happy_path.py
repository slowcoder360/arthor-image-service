"""s08 AC-4: generate_single happy path with injected fake client."""

from __future__ import annotations

import base64
from dataclasses import dataclass

import pytest

from _fake_openai import FakeAsyncOpenAI, b64_png_bytes, make_generate_response


@dataclass
class FakeStyleProfile:
    id: str = "sp-1"
    register: str = "photographic"


@dataclass
class _SafeArea:
    mode: str = "center"
    inset_pct: int = 10


@dataclass
class _Dim:
    w: int = 1024
    h: int = 1024


@dataclass
class FakeSlot:
    slot_id: str = "s-hero"
    intent: str = "hero shot"


@pytest.mark.asyncio
async def test_generate_single_returns_provider_result_with_decoded_bytes():
    try:
        from app.providers.openai_image import OpenAIImageProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: OpenAIImageProvider must be importable ({exc})")

    b64 = b64_png_bytes()
    fake = FakeAsyncOpenAI(generate_response=make_generate_response(b64=b64))
    provider = OpenAIImageProvider(client=fake)

    result = await provider.generate_single(
        prompt="a serene workspace",
        dimensions=(1024, 1024),
        seed=42,
        style_profile=FakeStyleProfile(),
        reference_images=None,
    )

    assert result.image_bytes == base64.b64decode(b64), (
        "AC-4: generate_single must base64-decode the response and put bytes on ProviderResult"
    )
    assert result.determinism_level == "best-effort", (
        "AC-4: determinism_level must be 'best-effort' for OpenAI image API"
    )
    assert result.seed is None, (
        "AC-4: ProviderResult.seed must be None (OpenAI image API does not honor user seed)"
    )
    assert result.latency_ms > 0, "AC-4: latency_ms must be positive"
    assert result.provider == "openai_image", "AC-4: provider must equal 'openai_image'"
    assert isinstance(result.cost_cents, int) and result.cost_cents >= 0, (
        "AC-4: cost_cents must be a non-negative int from the cost table"
    )
