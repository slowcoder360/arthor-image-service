"""s06 AC-5: when triggers are not all met, no LLM call; flag stays False."""

from __future__ import annotations

import pytest

from _fixtures.mood_llm import FakeMoodLLMClient
from _payload_helpers import fallback_skipped_payload, import_payload_v1


@pytest.mark.asyncio
async def test_no_llm_call_when_hint_mood_present():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: resolver must be importable ({exc})")

    fake = FakeMoodLLMClient(response=["should-not-be-used"])
    payload = PayloadV1.model_validate(fallback_skipped_payload())
    profile = await resolve_style_profile(payload, mood_llm_client=fake)

    assert fake.calls == [], (
        "AC-5: LLM client must NOT be invoked when triggers are not all met"
    )
    assert profile.resolver_used_llm_fallback is False, (
        "AC-5: resolver_used_llm_fallback must be False when no fallback was used"
    )
