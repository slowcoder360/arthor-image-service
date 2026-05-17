"""s06 AC-3: healthcare industry extensions add YMYL strings to do_not."""

from __future__ import annotations

import pytest

from _payload_helpers import import_payload_v1, with_industry


HEALTHCARE_EXPECTED = (
    "no patient faces",
    "no medical procedures shown explicitly",
)


@pytest.mark.asyncio
async def test_healthcare_industry_adds_ymyl_extensions():
    PayloadV1 = import_payload_v1()
    try:
        from app.style.resolver import resolve_style_profile  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-3: resolver must be importable ({exc})")

    raw = with_industry("healthcare-clinic")
    payload = PayloadV1.model_validate(raw)
    profile = await resolve_style_profile(payload)

    do_not = list(profile.do_not)
    for entry in HEALTHCARE_EXPECTED:
        assert entry in do_not, (
            f"AC-3: healthcare industry must add {entry!r} to do_not (matched via 'healthcare' substring)"
        )


def test_industry_do_not_extensions_table_exists():
    try:
        from app.style.defaults import (  # type: ignore[import-not-found]
            INDUSTRY_DO_NOT_EXTENSIONS,
        )
    except ImportError as exc:
        pytest.fail(f"AC-3: INDUSTRY_DO_NOT_EXTENSIONS must be importable ({exc})")
    assert "healthcare" in INDUSTRY_DO_NOT_EXTENSIONS, (
        "AC-3: INDUSTRY_DO_NOT_EXTENSIONS must declare a 'healthcare' key"
    )
    healthcare_entries = INDUSTRY_DO_NOT_EXTENSIONS["healthcare"]
    for entry in HEALTHCARE_EXPECTED:
        assert entry in healthcare_entries, (
            f"AC-3: 'healthcare' extension must include {entry!r}"
        )
