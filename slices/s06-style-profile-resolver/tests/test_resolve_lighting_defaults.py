"""s06 AC-4: missing hint.lighting → DEFAULT_LIGHTING_BY_REGISTER[register]."""

from __future__ import annotations

import pytest

from _payload_helpers import import_payload_v1, with_register


@pytest.mark.parametrize("register", ["photographic", "illustrated", "mixed"])
@pytest.mark.asyncio
async def test_default_lighting_per_register(register):
    PayloadV1 = import_payload_v1()
    try:
        from app.style.defaults import (  # type: ignore[import-not-found]
            DEFAULT_LIGHTING_BY_REGISTER,
        )
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: defaults + resolver must be importable ({exc})")

    raw = with_register(register)
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)
    assert profile.lighting == DEFAULT_LIGHTING_BY_REGISTER[register], (
        f"AC-4: register='{register}' missing hint must use DEFAULT_LIGHTING_BY_REGISTER value; "
        f"got {profile.lighting!r}"
    )
