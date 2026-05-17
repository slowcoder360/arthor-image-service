"""Shared payload fixtures for s04 tests. NOT a test module (no test_ prefix)."""

from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any


def mvp_payload() -> dict[str, Any]:
    """Minimum-viable payload per ADR-0010 §'Minimum-viable payload'."""
    return {
        "payload_version": "1.0",
        "idempotency_key": "abcdef-mvp-001",
        "site_id": str(uuid.uuid4()),
        "agent_run_id": str(uuid.uuid4()),
        "callback_url": "https://arthor-ai.example.com/callbacks/images",
        "business": {
            "site_name": "Acme Co",
            "industry": "professional-services",
            "icp_summary": "small businesses in metro areas",
            "value_prop": "make ops easier",
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
            "tone": "warm and professional",
            "notes": [],
            "style_direction": "",
            "reference_likes": [],
            "do_not": [],
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
            "do_not": ["no neon", "no overlay text"],
            "must_include": [],
        },
        "pack": {
            "pack_id": "pack-mvp-001",
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
                    "page_h1": None,
                    "section_heading": None,
                    "body_excerpt": None,
                    "cta_label": None,
                },
                "subject": {
                    "primary": "interior workspace, soft daylight",
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


def maximal_payload() -> dict[str, Any]:
    """Every optional field populated, two slots, customer reference assets, etc."""
    payload = deepcopy(mvp_payload())
    payload["idempotency_key"] = "abcdef-max-001"
    payload["business"].update(
        {
            "proof_points": ["20+ years in business", "Inc 5000 honoree"],
            "forbidden_subjects": ["competitor logos"],
            "priority_services": ["consulting", "implementation"],
        }
    )
    payload["location"].update(
        {"city": "Austin", "region": "TX", "service_areas": ["Austin", "Dallas"]}
    )
    payload["brand_voice"].update(
        {
            "notes": ["use second-person voice"],
            "style_direction": "minimalist editorial",
            "reference_likes": ["Linear", "Stripe"],
            "do_not": ["no jargon"],
        }
    )
    payload["brand_visual"].update(
        {
            "logo_asset_id": "asset_logo_001",
            "customer_reference_assets": [
                {
                    "asset_id": "cust_001",
                    "role": "interior",
                    "url": "https://cdn.example.com/cust_001.jpg",
                    "palette_hex": ["#0A4B6F", "#F4A261"],
                }
            ],
        }
    )
    payload["style_profile_hint"].update(
        {
            "camera_language": "35mm, shallow depth of field",
            "composition_rules": ["rule of thirds", "leading lines"],
            "color_grading": "muted, slightly warm",
            "texture": "matte, fine grain",
            "era_mood": "modern editorial",
            "must_include": ["natural light"],
        }
    )
    payload["pack"]["default_provider_hint"] = "openai_image"
    payload["pack"]["slot_order"] = ["s-hero", "s-services"]
    payload["slots"].append(
        {
            "slot_id": "s-services",
            "ordinal": 1,
            "page": "/services",
            "route": {
                "name": "services",
                "template": "service_index",
                "target_keyword": "consulting",
            },
            "section": {"section_type": "services", "section_instance_id": "svc-1"},
            "slot_kind": "section_accent",
            "intent": "showcase the breadth of consulting services with calm focus",
            "copy_context": {
                "page_h1": "Our Services",
                "section_heading": "What we do",
                "body_excerpt": "We help operators ship.",
                "cta_label": "Get in touch",
            },
            "subject": {
                "primary": "abstract gradient with soft geometry",
                "setting": "studio backdrop",
                "props": ["paper texture"],
                "people_policy": {"faces_allowed": False, "notes": "no faces"},
            },
            "camera": {"framing": "medium", "angle": "low", "lens_feel": "50mm"},
            "lighting_mood": {
                "mood_tokens": ["calm", "warm"],
                "contrast": "low",
            },
            "layout": {
                "aspect_ratio": "4:3",
                "dimensions": {"w": 1600, "h": 1200},
                "safe_area": {"mode": "all", "inset_pct": 8},
                "overlay_text_risk": False,
            },
            "count": 1,
            "provider_hint": "google_nano_banana",
            "condition_on_slot_id": "s-hero",
        }
    )
    return payload
