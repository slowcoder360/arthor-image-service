"""Local dev driver: sign a PayloadV1 and POST it to a running arthor-image-service.

Usage:
    python scripts/send_request.py preview     # POST /images/style-profile/preview (default)
    python scripts/send_request.py generate    # POST /images/asset-pack/generate

Reads FASTAPI_ARTHOR_SHARED_SECRET from .env via app.config.get_settings(), signs the
exact request bytes with app.auth.hmac.sign_body, and prints the response. The payload
shape mirrors slices/s12-endpoint-style-preview/tests/_s12_helpers.py.
"""

from __future__ import annotations

import json
import sys
import uuid

import httpx

from app.auth.hmac import sign_body
from app.config import get_settings

BASE_URL = "http://localhost:8010"
ENDPOINTS = {
    "preview": "/images/style-profile/preview",
    "generate": "/images/asset-pack/generate",
}


def build_payload() -> dict:
    return {
        "payload_version": "1.0",
        "idempotency_key": f"dev-{uuid.uuid4()}",
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
            "city": "Austin",
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
            "pack_id": "pack-dev",
            "base_seed": 100,
            "slot_order": ["s-0"],
            "reference_policy": {
                "hero_slot_id": "s-0",
                "condition_non_hero_slots_on_hero": False,
                "allow_user_reference_conditioning": False,
            },
            "default_provider_hint": "openai_image",
        },
        "slots": [
            {
                "slot_id": "s-0",
                "ordinal": 0,
                "page": "/",
                "route": {"name": None, "template": None, "target_keyword": None},
                "section": {"section_type": "hero", "section_instance_id": None},
                "slot_kind": "hero",
                "intent": "establish brand mood",
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
                "camera": {"framing": "wide", "angle": "eye-level", "lens_feel": "35mm"},
                "lighting_mood": {"mood_tokens": [], "contrast": "medium"},
                "layout": {
                    "aspect_ratio": "16:9",
                    "dimensions": {"w": 1024, "h": 1024},
                    "safe_area": {"mode": "center", "inset_pct": 10},
                    "overlay_text_risk": True,
                },
                "count": 1,
                "provider_hint": None,
                "condition_on_slot_id": None,
            }
        ],
    }


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if which not in ENDPOINTS:
        print(f"unknown endpoint '{which}'; choose one of {list(ENDPOINTS)}")
        return 2

    secret = get_settings().fastapi_arthor_shared_secret
    if not secret:
        print("FASTAPI_ARTHOR_SHARED_SECRET is unset (.env)")
        return 2

    body = json.dumps(build_payload()).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Arthor-Signature": sign_body(secret, body),
    }
    url = BASE_URL + ENDPOINTS[which]
    print(f"POST {url}  ({len(body)} bytes)")
    resp = httpx.post(url, content=body, headers=headers, timeout=180.0)
    print(f"status: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
