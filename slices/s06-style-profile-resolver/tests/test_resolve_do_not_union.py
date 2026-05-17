"""s06 AC-4: do_not is a unioned, deduped sequence: brand_voice → hint → defaults → industry extension."""

from __future__ import annotations

import pytest

from _payload_helpers import base_payload_dict, import_payload_v1


@pytest.mark.asyncio
async def test_do_not_union_no_duplicates_and_brand_voice_first():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.defaults import DEFAULT_DO_NOT  # type: ignore[import-not-found]
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-4: defaults + resolver must be importable ({exc})")

    raw = base_payload_dict()
    raw["brand_voice"]["do_not"] = ["no jargon", "shared-entry"]
    raw["style_profile_hint"]["do_not"] = ["no neon", "shared-entry"]
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    do_not = list(profile.do_not)
    assert "no jargon" in do_not, "AC-4: brand_voice.do_not must contribute"
    assert "no neon" in do_not, "AC-4: hint.do_not must contribute"
    for default in DEFAULT_DO_NOT:
        assert default in do_not, f"AC-4: DEFAULT_DO_NOT entry {default!r} must contribute"

    assert do_not.count("shared-entry") == 1, (
        "AC-4: union must deduplicate strings that appear in multiple sources"
    )

    assert do_not.index("no jargon") < do_not.index("no neon"), (
        "AC-4: brand_voice.do_not must precede hint.do_not in the unioned order"
    )
    assert do_not.index("no neon") < do_not.index(DEFAULT_DO_NOT[0]), (
        "AC-4: hint.do_not must precede DEFAULT_DO_NOT in the unioned order"
    )
