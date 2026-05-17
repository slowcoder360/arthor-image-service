"""s11 shared helpers: payload builder mirroring s10 + a prior-pack seeder for regenerate tests.

These tests assume the same PayloadV1 schema s10 produces. The seeder writes a
complete prior pack run (agent_runs + image_request_payloads + external_media_assets
with status='uploaded') so the regenerate route + worker can be exercised against it.
"""

from __future__ import annotations

import json
import uuid
from typing import Any


def build_payload(num_slots: int = 2, idem_key: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "payload_version": "1.0",
        "idempotency_key": idem_key or f"s11-{uuid.uuid4()}",
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
            "pack_id": "pack-s11",
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


async def seed_prior_pack_run(
    conn,
    payload: dict[str, Any],
    *,
    run_id: uuid.UUID | None = None,
    asset_id: uuid.UUID | None = None,
    slot_id: str = "s-0",
    seed: int = 100,
    prompt_hash: str = "deadbeef00",
) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert a complete prior pack run that s11 can regenerate from.

    Writes:
      - agent_runs (run_type='image_pack_generation', status='complete', cost_cents=1)
      - image_request_payloads (with the full payload)
      - external_media_assets (status='uploaded', metadata={slot_id, seed, prompt_hash})

    Returns (run_id, asset_id).
    """
    run_id = run_id or uuid.uuid4()
    asset_id = asset_id or uuid.uuid4()
    await conn.execute(
        """
        INSERT INTO agent_runs (id, run_type, status, site_id, metadata, cost_cents)
        VALUES ($1, 'image_pack_generation', 'complete', $2, $3::jsonb, 1)
        """,
        run_id,
        uuid.UUID(payload["site_id"]),
        json.dumps({"site_id": payload["site_id"], "style_profile": {}}),
    )
    await conn.execute(
        """
        INSERT INTO image_request_payloads (agent_run_id, idempotency_key, payload)
        VALUES ($1, $2, $3::jsonb)
        """,
        run_id,
        payload["idempotency_key"],
        json.dumps(payload),
    )
    await conn.execute(
        """
        INSERT INTO external_media_assets
          (id, provider, status, agent_run_id, site_id, metadata)
        VALUES ($1, 'openai_image', 'uploaded', $2, $3, $4::jsonb)
        """,
        asset_id,
        run_id,
        uuid.UUID(payload["site_id"]),
        json.dumps({"slot_id": slot_id, "seed": seed, "prompt_hash": prompt_hash}),
    )
    return run_id, asset_id


async def cleanup_run(conn, *run_ids: uuid.UUID) -> None:
    for run_id in run_ids:
        await conn.execute(
            "DELETE FROM external_media_assets WHERE agent_run_id = $1", run_id
        )
        await conn.execute("DELETE FROM tool_calls WHERE run_id = $1", run_id)
        await conn.execute(
            "DELETE FROM image_request_payloads WHERE agent_run_id = $1", run_id
        )
    for run_id in run_ids:
        await conn.execute("DELETE FROM agent_runs WHERE parent_run_id = $1", run_id)
        await conn.execute("DELETE FROM agent_runs WHERE id = $1", run_id)
