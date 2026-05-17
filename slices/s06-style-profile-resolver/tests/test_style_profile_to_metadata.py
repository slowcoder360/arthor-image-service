"""s06 AC-6: style_profile_to_metadata returns the ADR-0009 §3 dict shape exactly."""

from __future__ import annotations

import pytest

from _payload_helpers import base_payload_dict, import_payload_v1


REQUIRED_KEYS = {
    "id",
    "palette",
    "lighting",
    "register",
    "composition",
    "camera_language",
    "color_grading",
    "mood",
    "do_not",
    "must_include",
    "resolver_version",
    "resolver_used_llm_fallback",
}


@pytest.mark.asyncio
async def test_metadata_dict_has_all_documented_keys():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.resolver import (  # type: ignore[import-not-found]
            resolve_style_profile,
            style_profile_to_metadata,
        )
    except ImportError as exc:
        pytest.fail(f"AC-6: resolver must be importable ({exc})")

    payload = PayloadV1.model_validate(base_payload_dict())
    profile = await resolve_style_profile(payload)
    metadata = style_profile_to_metadata(profile)
    missing = REQUIRED_KEYS - set(metadata.keys())
    assert not missing, (
        f"AC-6: style_profile_to_metadata is missing keys {missing}; got {sorted(metadata.keys())!r}"
    )
    assert metadata["resolver_version"] == "1.0", (
        "AC-6: resolver_version must equal '1.0' in the persisted dict"
    )
