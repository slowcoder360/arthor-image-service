"""Deterministic hero reference plan — ingress refs → OpenAI edit selection."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from app.payload.hero_models import HeroCandidatesRequest
from app.style.hero_visual_strategy import AuthenticityMode, resolve_authenticity_mode

logger = logging.getLogger(__name__)

REFERENCE_PLAN_VERSION = "1.0"

_EDIT_ROLES = frozenset({"interior", "team", "ambient"})


def _asset_entry(ref: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "asset_id": ref.asset_id,
        "role": ref.role,
        "url": str(ref.url),
        "usage_hint": ref.usage_hint,
        "likeness_consent": bool(ref.likeness_consent),
        "edit_eligible": False,
    }
    if ref.note:
        entry["note"] = ref.note
    if ref.palette_hex:
        entry["palette_hex"] = [str(c) for c in ref.palette_hex]
    return entry


def build_hero_reference_plan(request: HeroCandidatesRequest) -> dict[str, Any] | None:
    """Build deterministic reference plan for run metadata (no URL fetch)."""
    refs = request.brand_visual.customer_reference_assets
    if not refs:
        return None

    auth: AuthenticityMode = resolve_authenticity_mode(request)
    assets: list[dict[str, Any]] = []
    warnings: list[str] = []
    edit_asset_id: str | None = None

    for ref in refs:
        entry = _asset_entry(ref)
        if ref.role == "team" and not ref.likeness_consent:
            warnings.append(f"team_ref_{ref.asset_id}_missing_likeness_consent")
        elif ref.role in _EDIT_ROLES:
            entry["edit_eligible"] = True
            if edit_asset_id is None:
                if ref.role != "team" or ref.likeness_consent:
                    edit_asset_id = ref.asset_id
        assets.append(entry)

    return {
        "reference_plan_version": REFERENCE_PLAN_VERSION,
        "authenticity_mode": auth,
        "edit_enabled": edit_asset_id is not None,
        "edit_asset_id": edit_asset_id,
        "edit_path": "openai_edit" if edit_asset_id else None,
        "provider_uses_first_ref_only": True,
        "assets": assets,
        "warnings": warnings,
    }


async def resolve_reference_bytes_for_plan(
    plan: dict[str, Any] | None,
    *,
    fetch_url: Callable[[str], Awaitable[bytes]],
) -> tuple[list[bytes], dict[str, Any] | None]:
    """Fetch bytes for the selected edit reference; mutates plan resolve fields."""
    if plan is None or not plan.get("edit_enabled"):
        return [], plan

    edit_id = plan.get("edit_asset_id")
    if not edit_id:
        return [], plan

    resolved: list[bytes] = []
    for asset in plan.get("assets") or []:
        if not isinstance(asset, dict) or asset.get("asset_id") != edit_id:
            continue
        url = str(asset.get("url") or "")
        if not url:
            asset["resolved"] = False
            asset["resolve_error"] = "missing_url"
            break
        try:
            data = await fetch_url(url)
            asset["resolved"] = True
            asset["byte_len"] = len(data)
            resolved.append(data)
        except Exception as exc:
            logger.warning("hero reference fetch failed asset_id=%s: %s", edit_id, exc)
            asset["resolved"] = False
            asset["resolve_error"] = str(exc)
        break

    if not resolved:
        plan = dict(plan)
        plan["edit_enabled"] = False
        plan["edit_path"] = None
        plan.setdefault("warnings", [])
        if isinstance(plan["warnings"], list):
            plan["warnings"] = [*plan["warnings"], f"reference_fetch_failed:{edit_id}"]

    return resolved, plan
