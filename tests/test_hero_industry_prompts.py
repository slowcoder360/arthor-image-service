"""Industry-specific hero prompt guards (cohort review regressions)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from app.payload.hero_models import HeroCandidatesRequest, hero_request_to_payload_v1
from app.style.hero_archetypes import resolve_industry
from app.style.hero_prompt_compiler import compile_hero_triad_prompts
from app.style.hero_visual_strategy import resolve_scene_archetype
from app.style.resolver import resolve_style_profile
from tests.test_hero_candidates import _build_hero_request

ROOT = Path(__file__).resolve().parents[1]
_COHORT_EVAL = ROOT / "scripts" / "hero_cohort_eval.py"


def _load_cohort_eval_module():
    spec = importlib.util.spec_from_file_location("hero_cohort_eval", _COHORT_EVAL)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _req_for_industry(industry: str) -> HeroCandidatesRequest:
    raw = _build_hero_request()
    raw["business"]["industry"] = industry
    raw["business"]["icp_summary"] = "local families seeking service"
    return HeroCandidatesRequest.model_validate(raw)


@pytest.mark.asyncio
async def test_home_services_prompt_benefit_subject_not_doorway():
    req = _req_for_industry("hvac repair")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "home comfort" in text or "thermostat" in text or "vent" in text
    assert "welcoming threshold" not in text
    assert "doorway consult" not in text or "exclude" in text
    assert resolve_scene_archetype(req, 1) == "desk_side_guidance"


@pytest.mark.asyncio
async def test_home_services_story_wip_not_patio_table():
    req = _req_for_industry("hvac repair")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[1].prompt.lower()
    assert "work in progress" in text or "actively performing" in text
    assert resolve_scene_archetype(req, 1) == "desk_side_guidance"


@pytest.mark.asyncio
async def test_healthcare_prompt_benefit_subject_trade_specific():
    req = _req_for_industry("physical therapy clinic")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "movement" in text or "therapy" in text or "exercise" in text
    assert "welcoming threshold" not in text
    assert "scrubs" in text or "clinical" in text or "white coat" in text
    assert resolve_industry("physical therapy clinic").label == "healthcare"


@pytest.mark.asyncio
async def test_legal_index_zero_benefit_desk_counsel():
    req = _req_for_industry("personal injury law")
    assert resolve_scene_archetype(req, 0) == "desk_side_guidance"
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "attorney" in text and "desk" in text
    assert "welcoming threshold" not in text


@pytest.mark.asyncio
async def test_dental_prompt_includes_people_diversity():
    req = _req_for_industry("dental")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "diversity" in text or "male" in text or "mixed" in text or "all-female" in text
    assert "dental" in text or "clinic" in text


@pytest.mark.asyncio
async def test_landscaping_resolves_outdoor_services():
    req = _req_for_industry("landscaping")
    assert resolve_industry("landscaping").label == "outdoor_services"
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "outdoor" in text or "yard" in text or "lawn" in text
    assert "kitchen" in text or "couch" in text or "interior" in text


def test_canary_matrix_has_thirty_slugs():
    mod = _load_cohort_eval_module()
    assert len(mod.CANARY_SCENARIOS) == 30
    slugs = [s["slug"] for s in mod.CANARY_SCENARIOS]
    assert len(slugs) == len(set(slugs))


def test_canary_routing_matches_expected_labels():
    mod = _load_cohort_eval_module()
    mismatches = []
    for scenario in mod.CANARY_SCENARIOS:
        resolved, expected = mod.check_routing(scenario)
        if expected:
            mismatches.append((scenario["slug"], scenario["business"]["industry"], resolved, expected))
    assert mismatches == []


def test_canary_palette_drift_does_not_fail_qa():
    mod = _load_cohort_eval_module()
    assert mod.qa_pass_from_failure_mode(has_url=True, failure_mode="palette_drift") is True
    assert mod.qa_pass_from_failure_mode(has_url=True, failure_mode="rendered_text") is False
    assert mod.qa_pass_from_failure_mode(has_url=True, failure_mode="safe_zone_violation") is False
    assert mod.qa_pass_from_failure_mode(has_url=False, failure_mode="palette_drift") is False


@pytest.mark.asyncio
async def test_home_services_people_policy_candid_not_lens_stare():
    req = _req_for_industry("hvac repair")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "three-quarter" in text or "candid" in text or "side glance" in text
    assert "not direct" in text or "not stock portrait stare" in text
    assert resolve_scene_archetype(req, 0) == "threshold_invitation"


@pytest.mark.asyncio
async def test_healthcare_patient_street_clothes_provider_clinical():
    req = _req_for_industry("physical therapy clinic")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "street clothes" in text or "everyday" in text
    assert "scrubs" in text or "white coat" in text or "clinical" in text
    assert "both subjects in medical attire" in text or "never both" in text


def test_routing_garage_door_home_services():
    assert resolve_industry("garage door repair").label == "home_services"


def test_routing_tree_removal_outdoor_services():
    assert resolve_industry("tree removal service").label == "outdoor_services"


def test_routing_fencing_outdoor_services():
    assert resolve_industry("fence installation").label == "outdoor_services"


def test_routing_concrete_paving_general_services():
    assert resolve_industry("concrete paving contractor").label == "general_services"


@pytest.mark.asyncio
async def test_plumbing_setting_is_interior_not_exterior_backdrop():
    req = _req_for_industry("plumbing service")
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    prompt = compile_hero_triad_prompts(req, profile)[0].prompt
    setting = next(b for b in prompt.split("\n\n") if b.startswith("Setting:")).lower()
    assert "interior home plumbing" in setting or "under-sink" in setting
    assert "roofline" not in setting and "garage facade" not in setting
    assert "never outdoor" in setting or "indoor water heater" in setting


@pytest.mark.asyncio
async def test_restaurant_index_zero_environment_benefit():
    req = _req_for_industry("restaurant")
    assert resolve_scene_archetype(req, 0) == "environment_warmth"
    profile = await resolve_style_profile(hero_request_to_payload_v1(req))
    text = compile_hero_triad_prompts(req, profile)[0].prompt.lower()
    assert "dining" in text or "plated food" in text or "restaurant interior" in text
    assert "desk_side_guidance" not in text
    assert "plan conversation at a side table" not in text


def test_canary_dry_run_cli():
    proc = subprocess.run(
        [sys.executable, str(_COHORT_EVAL), "--scenario-set", "canary", "--dry-run"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "30 canary slug(s)" in proc.stdout
    assert "dental (dental)" in proc.stdout
    assert "orthodontics (dental)" in proc.stdout


def test_canary_payload_records_search_variant_only():
    mod = _load_cohort_eval_module()
    scenario = next(s for s in mod.CANARY_SCENARIOS if s["slug"] == "dental")
    payload = mod.build_payload(scenario, replicate=0, hero_viewport="desktop", scenario_set="canary")
    assert payload["generation_mode"] == "live"
    assert payload["variants"][0]["tone_angle"] == "search"
    assert len(payload["variants"]) == 3
    assert payload["_eval_meta"]["expected_label"] == "dental"
