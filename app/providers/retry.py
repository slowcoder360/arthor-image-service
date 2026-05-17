"""Retry wrapper for provider calls (intake decision E — one retry, new seed)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.providers.openai_image import ProviderError


class RetryExhausted(Exception):
    """All attempts failed; last failure is chained as __cause__."""


async def with_retry[T](
    fn: Callable[[int | None], Awaitable[T]],
    *,
    max_retries: int = 1,
    base_seed: int | None = None,
    new_seed_fn: Callable[[int], int] = lambda s: s + 1,
) -> T:
    """Retry on ProviderError / TimeoutError; second attempt uses ``new_seed_fn(base_seed)``."""
    seed: int | None = base_seed
    for attempt in range(max_retries + 1):
        try:
            return await fn(seed)
        except (ProviderError, TimeoutError) as exc:
            if attempt == max_retries:
                raise RetryExhausted("provider call retries exhausted") from exc
            seed = None if base_seed is None else new_seed_fn(base_seed)
