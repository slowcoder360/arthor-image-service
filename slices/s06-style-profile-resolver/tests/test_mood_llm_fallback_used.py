"""s06 AC-5: when all triggers met, LLM client is called and result lands in profile.mood."""

from __future__ import annotations

import pytest

from _fixtures.mood_llm import FakeMoodLLMClient
from _payload_helpers import fallback_trigger_payload, import_payload_v1


@pytest.mark.asyncio
async def test_llm_called_and_result_used_when_triggers_all_met():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: resolver must be importable ({exc})")

    fake = FakeMoodLLMClient(response=["calm", "trusted", "expert"])
    payload = PayloadV1.model_validate(fallback_trigger_payload())
    profile = await resolve_style_profile(payload, mood_llm_client=fake)

    assert len(fake.calls) == 1, (
        f"AC-5: LLM client must be called exactly once when triggers met; got {len(fake.calls)}"
    )
    assert "calm" in profile.mood, "AC-5: returned mood adjectives must appear in profile.mood"
    assert "expert" in profile.mood, "AC-5: returned mood adjectives must appear in profile.mood"
    assert profile.resolver_used_llm_fallback is True, (
        "AC-5: resolver_used_llm_fallback must be True when fallback ran"
    )
