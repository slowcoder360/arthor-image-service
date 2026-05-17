"""s08 AC-5: generate_pack_consistent raises NotImplementedError with the documented message."""

from __future__ import annotations

import pytest

from _fake_openai import FakeAsyncOpenAI


@pytest.mark.asyncio
async def test_generate_pack_consistent_raises_not_implemented_with_documented_message():
    try:
        from app.providers.openai_image import OpenAIImageProvider  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: OpenAIImageProvider must be importable ({exc})")

    provider = OpenAIImageProvider(client=FakeAsyncOpenAI())
    with pytest.raises(NotImplementedError) as exc_info:
        await provider.generate_pack_consistent(prompts=[], style_profile=None, seed=0)

    msg = str(exc_info.value).lower()
    assert "pack-consistent" in msg or "pack consistent" in msg, (
        "AC-5: NotImplementedError message must explain that OpenAI does not support pack-consistent generation"
    )
