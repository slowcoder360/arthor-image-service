"""s06 AC-5: LLM TimeoutError → defaults ['approachable', 'credible']; flag stays True."""

from __future__ import annotations

import asyncio

import pytest

from _fixtures.mood_llm import FakeMoodLLMClient
from _payload_helpers import fallback_trigger_payload, import_payload_v1


@pytest.mark.asyncio
async def test_llm_timeout_uses_documented_defaults_and_flags_fallback():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-5: resolver must be importable ({exc})")

    fake = FakeMoodLLMClient(raise_exc=asyncio.TimeoutError("synthetic timeout"))
    payload = PayloadV1.model_validate(fallback_trigger_payload())
    profile = await resolve_style_profile(payload, mood_llm_client=fake)

    assert profile.mood == ["approachable", "credible"], (
        f"AC-5: TimeoutError must yield mood ['approachable', 'credible']; got {profile.mood!r}"
    )
    assert profile.resolver_used_llm_fallback is True, (
        "AC-5: resolver_used_llm_fallback must be True even when the LLM call failed"
    )
