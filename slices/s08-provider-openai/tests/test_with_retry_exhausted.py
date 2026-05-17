"""s08 AC-6: with_retry raises RetryExhausted wrapping the original after both calls fail."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_with_retry_raises_retry_exhausted_when_both_fail():
    try:
        from app.providers.openai_image import ProviderError  # type: ignore[import-not-found]
        from app.providers.retry import RetryExhausted, with_retry  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-6: with_retry / RetryExhausted / ProviderError must be importable ({exc})"
        )

    async def fn(seed):
        raise ProviderError(f"failure at seed={seed}")

    with pytest.raises(RetryExhausted):
        await with_retry(fn, base_seed=42)
