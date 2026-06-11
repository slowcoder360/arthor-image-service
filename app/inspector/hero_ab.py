"""Hero-candidates A/B lab helpers (inspector GUI)."""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from typing import Any

import asyncpg
from pydantic import ValidationError

from app.payload.hero_models import HeroCandidatesRequest

PROVIDERS = (
    ("google_nano_banana", "Google (gemini)"),
    ("openai_image", "OpenAI"),
)

_TERMINAL_POLL_STATUSES = frozenset({"complete", "partial", "failed"})


def poll_status_terminal(status: str | None) -> bool:
    return status in _TERMINAL_POLL_STATUSES


def ab_session_needs_polling(
    *,
    google_run: str | None,
    openai_run: str | None,
    google_status: str | None,
    openai_status: str | None,
) -> bool:
    """True while any launched arm is still in-flight (client poll should continue)."""
    if google_run and not poll_status_terminal(google_status):
        return True
    if openai_run and not poll_status_terminal(openai_status):
        return True
    return False


def polling_status_note(
    *,
    google_run: str | None,
    openai_run: str | None,
    google_status: str | None,
    openai_status: str | None,
) -> str:
    """Human-readable hint for which arms are still being refreshed."""
    waiting: list[str] = []
    if google_run and not poll_status_terminal(google_status):
        waiting.append("Google")
    if openai_run and not poll_status_terminal(openai_status):
        waiting.append("OpenAI")
    if not waiting:
        return ""
    return f"Refreshing {', '.join(waiting)} — local DB status only (no provider API calls)."


_STALE_RUN_SECONDS = 300


async def reconcile_stale_hero_run(pool: Any, run_id: uuid.UUID) -> bool:
    """Mark orphaned ``running`` hero runs failed after worker/process loss."""
    from datetime import datetime, timezone

    from app.runs.agent_runs import update_run_status

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT status, started_at,
                   (SELECT count(*) FROM external_media_assets
                    WHERE agent_run_id = $1 AND status = 'uploaded') AS uploaded
            FROM agent_runs
            WHERE id = $1 AND run_type = 'hero_candidates_generation'
            """,
            run_id,
        )
    if row is None or str(row["status"]) != "running":
        return False
    if int(row["uploaded"] or 0) >= 3:
        return False
    started = row["started_at"]
    if started is None:
        return False

    age = (datetime.now(timezone.utc) - started).total_seconds()
    async with pool.acquire() as conn:
        pending = await conn.fetchval(
            """
            SELECT count(*) FROM external_media_assets
            WHERE agent_run_id = $1 AND status IN ('pending', 'generated')
            """,
            run_id,
        )
    # Orphan: worker gone but run still "running" (common after uvicorn restart).
    if int(pending or 0) == 0 and age >= 120:
        pass
    elif age < _STALE_RUN_SECONDS:
        return False
    await update_run_status(
        pool,
        run_id,
        status="failed",
        error="stale_orphaned_run: worker interrupted (restart or crash)",
        finished=True,
    )
    return True


def default_hero_payload() -> dict[str, Any]:
    """Canonical sample matching arthor-ai ``heroCandidatesRequestSchema``."""
    site_id = str(uuid.uuid4())
    return {
        "site_id": site_id,
        "idempotency_key": f"hero-ab:{site_id}:sample",
        "business": {
            "site_name": "Acme Dental",
            "industry": "dental",
            "icp_summary": "local families seeking preventive care",
            "value_prop": "gentle, modern dentistry with same-week appointments",
            "proof_points": [],
            "forbidden_subjects": [],
            "priority_services": [],
        },
        "location": {
            "mode": "local",
            "country": "US",
            "city": "Austin",
            "region": "TX",
            "service_areas": [],
        },
        "brand_voice": {
            "tone": "warm and reassuring",
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
            "lighting": "soft natural window light, welcoming interior",
            "camera_language": "",
            "composition_rules": [],
            "color_grading": "",
            "texture": "",
            "era_mood": None,
            "do_not": ["stock photo smiles", "clinical sterility"],
            "must_include": [],
        },
        "variants": [
            {
                "tone_angle": "search",
                "headline": "Find a dentist you trust in Austin",
                "subhead": "Same-week appointments for busy families",
            },
            {
                "tone_angle": "story",
                "headline": "Care that feels personal from the first visit",
                "subhead": "A calm office built around your comfort",
            },
            {
                "tone_angle": "offer",
                "headline": "New patient exam — book this week",
                "subhead": "Transparent pricing, no surprise fees",
            },
        ],
        "base_seed": 77,
        "default_provider_hint": "openai_image",
    }


def payload_for_provider(base: dict[str, Any], provider: str) -> dict[str, Any]:
    out = deepcopy(base)
    site_id = str(out.get("site_id") or uuid.uuid4())
    out["site_id"] = site_id
    out["default_provider_hint"] = provider
    out["idempotency_key"] = f"hero-ab:{provider}:{uuid.uuid4()}"
    return out


def parse_payload_json(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "Payload must be a JSON object"
    try:
        validated = HeroCandidatesRequest.model_validate(data)
    except ValidationError as exc:
        return None, exc.errors()[0]["msg"] if exc.errors() else str(exc)
    return validated.model_dump(mode="json"), None


def encode_signed_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


async def fetch_latest_hero_payload(pool: Any) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT payload
            FROM image_request_payloads
            WHERE payload_version IN ('hero_candidates.1', 'hero_candidates.2')
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
    if row is None:
        return None
    raw = row["payload"]
    if isinstance(raw, str):
        raw = json.loads(raw)
    return raw if isinstance(raw, dict) else None


async def fetch_recent_hero_runs(pool: Any, *, limit: int = 20) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT id, status, started_at, finished_at, cost_cents, metadata
            FROM agent_runs
            WHERE run_type = 'hero_candidates_generation'
            ORDER BY started_at DESC NULLS LAST
            LIMIT $1
            """,
            limit,
        )


async def poll_hero_run(pool: Any, run_id: uuid.UUID, settings: Any) -> dict[str, Any] | None:
    from app.routes.hero_candidates import _build_poll_response

    try:
        await reconcile_stale_hero_run(pool, run_id)
        return await _build_poll_response(pool, run_id, settings)
    except Exception:
        return None


async def fetch_run_provider_prompts(pool: Any, run_id: uuid.UUID) -> list[dict[str, Any]]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT metadata FROM agent_runs WHERE id = $1",
            run_id,
        )
    if row is None:
        return []
    md = row["metadata"]
    if isinstance(md, str):
        md = json.loads(md)
    if not isinstance(md, dict):
        return []
    raw = md.get("hero_provider_prompts") or []
    return [p for p in raw if isinstance(p, dict)]


async def run_provider_label(pool: Any, run_id: uuid.UUID) -> str:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT provider FROM external_media_assets
            WHERE agent_run_id = $1
            ORDER BY created_at ASC
            LIMIT 1
            """,
            run_id,
        )
    if row is None:
        return "—"
    return str(row["provider"] or "—")
