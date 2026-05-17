"""s09 AC-3 / AC-4: generate_pack_consistent returns N results in input order with style_profile_id stamped."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from _fake_genai import FakeGenAIClient


@dataclass
class FakeStyleProfile:
    id: str = "sp-fixed-123"
    register: str = "photographic"


@dataclass
class FakeSlotPrompt:
    text: str
    prompt_hash: str
    prompt_template_version: str = "1.0"
    dimensions: tuple[int, int] = (1024, 1024)


@pytest.mark.asyncio
async def test_pack_consistent_returns_n_results_in_input_order():
    try:
        from app.providers.google_nano_banana import GoogleNanoBananaProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: GoogleNanoBananaProvider must be importable ({exc})")

    fake = FakeGenAIClient(batch_response=[b"\x89PNGa", b"\x89PNGb", b"\x89PNGc"])
    provider = GoogleNanoBananaProvider(client=fake)

    prompts = [
        FakeSlotPrompt(text="hero", prompt_hash="h-1"),
        FakeSlotPrompt(text="services", prompt_hash="h-2"),
        FakeSlotPrompt(text="testimonials", prompt_hash="h-3"),
    ]
    style = FakeStyleProfile()

    results = await provider.generate_pack_consistent(
        prompts=prompts, style_profile=style, seed=7
    )

    assert len(results) == len(prompts), (
        f"AC-3: must return one result per prompt; got {len(results)} for {len(prompts)} prompts"
    )

    for r in results:
        shape = r.response_shape or {}
        assert shape.get("style_profile_id") == style.id, (
            f"AC-4: every response_shape must carry style_profile_id={style.id!r}; got {shape!r}"
        )
