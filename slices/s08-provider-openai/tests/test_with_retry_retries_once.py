"""s08 AC-6: with_retry retries once with new_seed_fn(seed) on ProviderError."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_with_retry_retries_once_on_provider_error():
    try:
        from app.providers.openai_image import ProviderError  # type: ignore[import-not-found]
        from app.providers.retry import with_retry  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: with_retry / ProviderError must be importable ({exc})")

    seeds_seen: list[int | None] = []

    async def fn(seed):
        seeds_seen.append(seed)
        if seed == 42:
            raise ProviderError("first call fails")
        return {"ok": True, "seed": seed}

    new_seed_calls: list[int] = []

    def new_seed_fn(s: int) -> int:
        new_seed_calls.append(s)
        return s + 1

    result = await with_retry(fn, base_seed=42, new_seed_fn=new_seed_fn)
    assert result == {"ok": True, "seed": 43}, (
        "AC-6: with_retry must return the second-call result on retry success"
    )
    assert seeds_seen == [42, 43], (
        f"AC-6: must call fn(42) then fn(43); got {seeds_seen!r}"
    )
    assert new_seed_calls == [42], (
        f"AC-6: new_seed_fn must be called exactly once with the base seed; got {new_seed_calls!r}"
    )
