"""s08 AC-6: with_retry returns first call's result without retrying when it succeeds."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_with_retry_returns_first_result_no_retry():
    try:
        from app.providers.retry import with_retry  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-6: with_retry must be importable ({exc})")

    calls: list[int | None] = []

    async def fn(seed):
        calls.append(seed)
        return {"ok": True, "seed": seed}

    result = await with_retry(fn, base_seed=42)
    assert result == {"ok": True, "seed": 42}, "AC-6: must return first result"
    assert calls == [42], (
        f"AC-6: with_retry must call fn exactly once on success; got calls={calls}"
    )
