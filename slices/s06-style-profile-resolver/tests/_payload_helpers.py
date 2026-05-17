"""Self-contained MVP-payload builder for s06 tests (mirrors s04's MVP shape)."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any


def base_payload_dict() -> dict[str, Any]:
    return {
        "payload_version": "1.0",
        "idempotency_key": "abcdef-s06-001",
        "site_id": str(uuid.uuid4()),
        "agent_run_id": str(uuid.uuid4()),
        "callback_url": "https://arthor-ai.example.com/cb",
        "business": {
            "site_name": "Acme",
            "industry": "professional-services",
            "icp_summary": "smb founders",
            "value_prop": "make ops easier and faster for everyone in the org",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": [],
        },
        "location": {
            "mode": "local",
            "country": "US",
            "city": None,
            "region": None,
            "service_areas": [],
        },
        "brand_voice": {
            "tone": "warm",
            "notes": [],
            "style_direction": "",
            "reference_likes": [],
            "do_not": ["no jargon"],
        },
        "brand_visual": {
            "palette": {
                "light": {
                    "primary": "#0A4B6F",
                    "secondary": "#F4A261",
                    "background": "#FFFFFF",
                    "foreground": "#111111",
                    "muted": "#999999",
                },
                "dark": {
                    "primary": "#0A4B6F",
                    "secondary": "#F4A261",
                    "background": "#0A0A0A",
                    "foreground": "#FAFAFA",
                    "muted": "#666666",
                },
            },
            "typography": {"sans": "Inter", "heading": "Inter"},
            "register_default": "photographic",
            "logo_asset_id": None,
            "customer_reference_assets": [],
        },
        "style_profile_hint": {
            "lighting": "soft, diffused, midday window light",
            "camera_language": "",
            "composition_rules": [],
            "color_grading": "",
            "texture": "",
            "era_mood": None,
            "do_not": ["no neon"],
            "must_include": [],
        },
        "pack": {
            "pack_id": "pack-s06-001",
            "base_seed": 42,
            "slot_order": ["s-hero"],
            "reference_policy": {
                "hero_slot_id": "s-hero",
                "condition_non_hero_slots_on_hero": True,
                "allow_user_reference_conditioning": False,
            },
            "default_provider_hint": None,
        },
        "slots": [
            {
                "slot_id": "s-hero",
                "ordinal": 0,
                "page": "/",
                "route": {"name": None, "template": None, "target_keyword": None},
                "section": {"section_type": "hero", "section_instance_id": None},
                "slot_kind": "hero",
                "intent": "establish brand mood and trust at first scroll",
                "copy_context": {
                    "page_h1": "Acme Co",
                    "section_heading": "Our work",
                    "body_excerpt": None,
                    "cta_label": None,
                },
                "subject": {
                    "primary": "interior workspace",
                    "setting": "office",
                    "props": [],
                    "people_policy": {"faces_allowed": False, "notes": None},
                },
                "camera": {
                    "framing": "wide",
                    "angle": "eye-level",
                    "lens_feel": "35mm",
                },
                "lighting_mood": {"mood_tokens": [], "contrast": "medium"},
                "layout": {
                    "aspect_ratio": "16:9",
                    "dimensions": {"w": 1920, "h": 1080},
                    "safe_area": {"mode": "center", "inset_pct": 10},
                    "overlay_text_risk": True,
                },
                "count": 1,
                "provider_hint": None,
                "condition_on_slot_id": None,
            }
        ],
    }


def with_register(register: str) -> dict[str, Any]:
    p = deepcopy(base_payload_dict())
    p["brand_visual"]["register_default"] = register
    p["style_profile_hint"]["lighting"] = ""
    return p


def with_industry(industry: str) -> dict[str, Any]:
    p = deepcopy(base_payload_dict())
    p["business"]["industry"] = industry
    return p


def fallback_trigger_payload() -> dict[str, Any]:
    p = deepcopy(base_payload_dict())
    p["style_profile_hint"]["era_mood"] = None
    p["brand_voice"]["tone"] = ""
    p["business"]["value_prop"] = "short"
    return p


def fallback_skipped_payload() -> dict[str, Any]:
    p = deepcopy(base_payload_dict())
    p["style_profile_hint"]["era_mood"] = "modern editorial"
    p["brand_voice"]["tone"] = "warm and confident"
    return p


def import_payload_v1():
    import pytest

    try:
        from app.payload.models import PayloadV1  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"s06 tests require `app.payload.models.PayloadV1` (s04). Not yet implemented ({exc})."
        )
    return PayloadV1
