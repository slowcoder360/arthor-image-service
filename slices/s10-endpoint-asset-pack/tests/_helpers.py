"""s10 shared helpers: payload builder + fake provider/callback fixtures."""

from __future__ import annotations

import asyncio
import json
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


def build_payload(num_slots: int = 2, idem_key: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "payload_version": "1.0",
        "idempotency_key": idem_key or f"s10-{uuid.uuid4()}",
        "site_id": str(uuid.uuid4()),
        "agent_run_id": str(uuid.uuid4()),
        "callback_url": "https://arthor-ai.example.com/cb",
        "business": {
            "site_name": "Acme",
            "industry": "professional-services",
            "icp_summary": "smb founders",
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
            "tone": "warm",
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
            "do_not": [],
            "must_include": [],
        },
        "pack": {
            "pack_id": "pack-s10",
            "base_seed": 100,
            "slot_order": [f"s-{i}" for i in range(num_slots)],
            "reference_policy": {
                "hero_slot_id": "s-0",
                "condition_non_hero_slots_on_hero": True,
                "allow_user_reference_conditioning": False,
            },
            "default_provider_hint": None,
        },
        "slots": [],
    }
    for i in range(num_slots):
        payload["slots"].append(
            {
                "slot_id": f"s-{i}",
                "ordinal": i,
                "page": "/",
                "route": {"name": None, "template": None, "target_keyword": None},
                "section": {
                    "section_type": "hero" if i == 0 else "services",
                    "section_instance_id": None,
                },
                "slot_kind": "hero" if i == 0 else "section_accent",
                "intent": "establish brand mood and trust at first scroll",
                "copy_context": {
                    "page_h1": "Acme",
                    "section_heading": None,
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
                    "dimensions": {"w": 1024, "h": 1024},
                    "safe_area": {"mode": "center", "inset_pct": 10},
                    "overlay_text_risk": True,
                },
                "count": 1,
                "provider_hint": None,
                "condition_on_slot_id": None if i == 0 else "s-0",
            }
        )
    return payload


@dataclass
class FakeProviderCall:
    kind: str
    slot_id: str | None
    seed: int | None
    has_reference: bool


class CallRecorder:
    def __init__(self):
        self.calls: list[FakeProviderCall] = []

    def record(self, call: FakeProviderCall) -> None:
        self.calls.append(call)
