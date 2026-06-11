"""Hero desktop → mobile seed (OpenAI edit reference path)."""

from __future__ import annotations

import uuid

import pytest

from app.orchestration.hero_worker import plan_hero_variant_regenerate
from app.payload.hero_models import HeroCandidatesRequest, hero_request_to_payload_v1
from app.style.hero_desktop_seed import DESKTOP_SEED_EDIT_MODIFIER
from app.style.resolver import resolve_style_profile
from tests.test_hero_candidates import _build_hero_request


def test_source_desktop_run_id_requires_mobile_viewport():
    raw = _build_hero_request()
    raw["source_desktop_run_id"] = str(uuid.uuid4())
    with pytest.raises(ValueError, match="source_desktop_run_id requires hero_viewport mobile"):
        HeroCandidatesRequest.model_validate(raw)


@pytest.mark.asyncio
async def test_mobile_from_desktop_requires_source_asset():
    hero_req = HeroCandidatesRequest.model_validate(_build_hero_request())
    style_profile = await resolve_style_profile(hero_request_to_payload_v1(hero_req))
    with pytest.raises(ValueError, match="mobile_from_desktop_requires_source_hero_asset_id"):
        plan_hero_variant_regenerate(
            hero_req,
            variant_index=0,
            edit_kind="mobile_from_desktop",
            style_profile=style_profile,
            original_seed=77,
        )


@pytest.mark.asyncio
async def test_mobile_from_desktop_recompiles_mobile_viewport_and_edit_modifier():
    hero_req = HeroCandidatesRequest.model_validate(_build_hero_request())
    style_profile = await resolve_style_profile(hero_request_to_payload_v1(hero_req))
    source_id = uuid.uuid4()

    compiled, req_eff, edit_meta = plan_hero_variant_regenerate(
        hero_req,
        variant_index=0,
        edit_kind="mobile_from_desktop",
        style_profile=style_profile,
        original_seed=77,
        source_hero_asset_id=source_id,
    )

    assert req_eff.hero_viewport == "mobile"
    assert edit_meta["source_hero_asset_id"] == str(source_id)
    assert DESKTOP_SEED_EDIT_MODIFIER.split()[0] in compiled.prompt
    assert compiled.hero_viewport == "mobile"


def test_hero_openai_provider_uses_high_quality():
    from app.config import Settings
    from app.providers.registry import get_provider

    settings = Settings()
    provider = get_provider("openai_image", settings, quality=settings.hero_openai_image_quality)
    assert provider._quality == "high"
