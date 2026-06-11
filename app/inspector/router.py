"""HTTP routes for the `/inspector` HTML UI.

Regenerate-slot actions POST to this app's ``/images/regenerate-slot`` over HTTP
(``httpx`` against ``localhost`` + ``PORT`` / ``UVICORN_PORT`` / default 8000), with the same
HMAC headers as any arthor-ai client. That keeps operator clicks and API calls on one code path
(ADR-0006).
"""

from __future__ import annotations

import hmac
import json
import os
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from app.auth.inspector_token import issue_inspector_cookie, require_inspector_token
from app.auth.sign import sign_outbound
from app.inspector import cost as cost_rollups
from app.inspector import hero_ab
from app.providers.image_model_costs import format_cost_table_markdown
from app.inspector import queries
from app.inspector.csrf import CSRF_COOKIE_NAME, issue_csrf_token, verify_csrf_token
from app.storage import UnsupersedeUnavailable, unsupersede_asset

_DIR = Path(__file__).resolve().parent
_TEMPLATES = Jinja2Templates(directory=str(_DIR / "templates"))

_public = APIRouter()
_protected = APIRouter(dependencies=[Depends(require_inspector_token)])


def inspector_http_client(base_url: str) -> httpx.AsyncClient:
    """Outbound client for same-process API calls (overridable in tests)."""

    return httpx.AsyncClient(base_url=base_url)


def _inspector_internal_api_base() -> str:
    port = os.environ.get("PORT") or os.environ.get("UVICORN_PORT") or "8010"
    return f"http://127.0.0.1:{port}"


def _render(
    request: Request,
    name: str,
    context: dict[str, Any],
    *,
    status_code: int = 200,
) -> Response:
    token = secrets.token_urlsafe(32)
    ctx = {**context, "request": request, "csrf_token": token}
    response = _TEMPLATES.TemplateResponse(
        request, name, ctx, status_code=status_code
    )
    issue_csrf_token(response, token, secure=request.url.scheme == "https")
    response.headers["Cache-Control"] = "no-store"
    return response


def _render_partial(
    request: Request,
    name: str,
    context: dict[str, Any],
    *,
    status_code: int = 200,
) -> Response:
    token = request.cookies.get(CSRF_COOKIE_NAME) or secrets.token_urlsafe(32)
    ctx = {**context, "request": request, "csrf_token": token}
    response = _TEMPLATES.TemplateResponse(
        request, name, ctx, status_code=status_code
    )
    issue_csrf_token(response, token, secure=request.url.scheme == "https")
    response.headers["Cache-Control"] = "no-store"
    return response


def _metadata_as_dict(meta: Any) -> dict[str, Any]:
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str):
        try:
            parsed = json.loads(meta)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _slot_key(slot_id: str) -> str:
    return str(slot_id).replace("/", "-").replace(" ", "_")


def _variant_dict(rec: Any) -> dict[str, Any]:
    meta = _metadata_as_dict(rec["metadata"])
    return {
        "r2_url": rec["r2_url"],
        "prompt_hash": meta.get("prompt_hash") or "—",
        "seed": meta.get("seed", "—"),
        "provider": rec["provider"],
        "cost_cents": rec["cost_cents"],
    }


def _grid_asset_dict(rec: Any) -> dict[str, Any]:
    meta = _metadata_as_dict(rec["metadata"])
    return {
        "id": rec["id"],
        "r2_url": rec["r2_url"],
        "slot_id": meta.get("slot_id", "—"),
    }


def _iteration_targets(
    assets_payload: list[dict[str, Any]], *, run_id: uuid.UUID
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    targets: list[dict[str, Any]] = []
    for a in assets_payload:
        if str(a["status"]) != "uploaded":
            continue
        sid = a["metadata"].get("slot_id")
        if not sid:
            continue
        slot_s = str(sid)
        if slot_s in seen:
            continue
        seen.add(slot_s)
        targets.append(
            {
                "slot_key": _slot_key(slot_s),
                "slot_id": slot_s,
                "asset_id": a["id"],
                "run_id": run_id,
                "regen_message": None,
                "soft_deleted": False,
            }
        )
    return targets


@_public.get("/login")
async def login_get(request: Request) -> Response:
    return _render(request, "login.html", {"error": None})


@_public.post("/login")
async def login_post(
    request: Request,
    token: str = Form(),
    csrf_token: str | None = Form(None),
) -> Response:
    verify_csrf_token(request, csrf_token)
    services = request.app.state.services
    settings = services.settings
    expected = settings.inspector_admin_token
    if expected is None:
        raise HTTPException(status_code=503, detail="inspector_admin_token_unset")
    if not hmac.compare_digest(token.encode("utf-8"), expected.encode("utf-8")):
        response = _render(
            request,
            "login.html",
            {"error": "Invalid token — check INSPECTOR_ADMIN_TOKEN and try again."},
        )
        return response
    redirect = RedirectResponse(url="/inspector/runs", status_code=303)
    issue_inspector_cookie(redirect, token)
    return redirect


@_protected.get("/cost")
async def inspector_cost_page(
    request: Request,
    date_from_q: date | None = Query(default=None, alias="date_from"),
    date_to_q: date | None = Query(default=None, alias="date_to"),
    site_id: uuid.UUID | None = Query(default=None),
    provider: str | None = Query(default=None),
) -> Response:
    eff_from, eff_to = date_from_q, date_to_q
    if eff_from is None and eff_to is None:
        eff_to = datetime.now(timezone.utc).date()
        eff_from = eff_to - timedelta(days=29)

    prov_s = ""
    if provider is not None and str(provider).strip():
        prov_s = str(provider).strip()

    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None
    dollar_fmt = cost_rollups.format_cents_as_dollars

    rows_per_run: list[cost_rollups.CostRow] = []
    rows_per_day: list[cost_rollups.DailyCostRow] = []
    rows_per_site: list[cost_rollups.SiteCostRow] = []
    rows_per_provider: list[cost_rollups.ProviderCostRow] = []
    rows_per_slot_type: list[cost_rollups.SlotTypeCostRow] = []

    if pool is not None:
        rows_per_run = await cost_rollups.cost_per_run(
            pool,
            limit=25,
            date_from=eff_from,
            date_to=eff_to,
            site_id=site_id,
            provider=prov_s or None,
        )
        rows_per_day = await cost_rollups.cost_per_day(
            pool,
            days=30,
            site_id=site_id,
            provider=prov_s or None,
            date_from=eff_from,
            date_to=eff_to,
        )
        rows_per_site = await cost_rollups.cost_per_site(
            pool,
            limit=25,
            date_from=eff_from,
            date_to=eff_to,
            provider=prov_s or None,
        )
        rows_per_provider = await cost_rollups.cost_per_provider(
            pool,
            date_from=eff_from,
            date_to=eff_to,
            site_id=site_id,
        )
        rows_per_slot_type = await cost_rollups.cost_per_slot_type(
            pool,
            date_from=eff_from,
            date_to=eff_to,
            site_id=site_id,
            provider=prov_s or None,
        )
        if site_id is not None:
            rows_per_site = [
                r for r in rows_per_site if getattr(r, "site_id", None) == site_id
            ]

    site_id_s = str(site_id) if site_id else ""

    return _render(
        request,
        "cost.html",
        {
            "date_from": eff_from,
            "date_to": eff_to,
            "site_id": site_id,
            "site_id_s": site_id_s,
            "provider_s": prov_s,
            "dollar_fmt": dollar_fmt,
            "rows_per_run": rows_per_run,
            "rows_per_day": rows_per_day,
            "rows_per_site": rows_per_site,
            "rows_per_provider": rows_per_provider,
            "rows_per_slot_type": rows_per_slot_type,
        },
    )


@_protected.get("/runs")
async def runs_list(
    request: Request,
    page: int = 1,
    run_type: str | None = None,
) -> Response:
    try:
        rt = queries.normalize_run_type_filter(run_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_run_type") from exc

    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None
    if pool is None:
        rows = []
        total = 0
        pages = 1
    else:
        rows, total, pages = await queries.load_runs_list(pool, page=page, run_type=rt)

    page_numbers = list(range(1, pages + 1))
    fragment = request.headers.get("HX-Request") == "true"
    tpl = "run_list.html"
    return _render(
        request,
        tpl,
        {
            "runs": rows,
            "page": max(page, 1),
            "total": total,
            "pages": pages,
            "page_numbers": page_numbers,
            "run_type_filter": rt or "",
            "fragment": fragment,
        },
    )


@_protected.get("/runs/{run_id}/grid")
async def run_pack_grid(request: Request, run_id: uuid.UUID) -> Response:
    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None
    if pool is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    rows = await queries.fetch_pack_grid_assets(pool, run_id)
    grid_assets = [_grid_asset_dict(r) for r in rows]
    return _render_partial(
        request,
        "pack_consistency_grid.html",
        {"grid_assets": grid_assets},
    )


@_protected.get("/runs/{run_id}")
async def run_detail(request: Request, run_id: uuid.UUID) -> Response:
    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None
    if pool is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    detail = await queries.load_run_detail(pool, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="run_not_found")

    run = detail["run"]
    payload_row = detail["payload_row"]
    payload_text = (
        json.dumps(payload_row["payload"], indent=2, sort_keys=True)
        if payload_row and payload_row["payload"] is not None
        else "—"
    )
    style_profile = detail["style_profile"]
    style_text = (
        json.dumps(style_profile, indent=2, sort_keys=True)
        if style_profile is not None
        else "—"
    )

    tool_calls_payload: list[dict[str, Any]] = []
    for tc in detail["tool_calls"]:
        res = tc["result"]
        result_text = (
            "—" if res is None else json.dumps(res, indent=2, sort_keys=True)
        )
        tool_calls_payload.append(
            {
                "id": tc["id"],
                "provider": tc["provider"],
                "model_version": tc["model_version"],
                "status": tc["status"],
                "cost_cents": tc["cost_cents"],
                "latency_ms": tc["latency_ms"],
                "args": tc["args"],
                "result_text": result_text,
            }
        )

    assets_payload: list[dict[str, Any]] = []
    for a in detail["assets"]:
        raw_meta = a["metadata"]
        if isinstance(raw_meta, dict):
            meta = raw_meta
        elif isinstance(raw_meta, str):
            try:
                meta = json.loads(raw_meta)
            except json.JSONDecodeError:
                meta = {}
        else:
            meta = {}
        assets_payload.append(
            {
                "id": a["id"],
                "provider": a["provider"],
                "status": a["status"],
                "model_version": a["model_version"],
                "r2_url": a["r2_url"],
                "metadata": meta,
                "created_at": a["created_at"],
                "palette_drift": bool(meta.get("palette_drift")),
            }
        )

    iteration_targets = _iteration_targets(assets_payload, run_id=run["id"])

    return _render(
        request,
        "run_detail.html",
        {
            "run": run,
            "payload_text": payload_text,
            "style_text": style_text,
            "assets": assets_payload,
            "tool_calls": tool_calls_payload,
            "iteration_targets": iteration_targets,
        },
    )


@_protected.get("/slots/{slot_id}/variants")
async def slot_variants(
    request: Request,
    slot_id: str,
    run_id: uuid.UUID,
) -> Response:
    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None
    if pool is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    rows = await queries.fetch_slot_variants(
        pool, slot_id=slot_id, anchor_run_id=run_id
    )
    variants = [_variant_dict(r) for r in rows]
    return _render_partial(
        request,
        "variants_grid.html",
        {"variants": variants},
    )


@_protected.post("/slots/{asset_id}/regenerate")
async def slot_regenerate(
    request: Request,
    asset_id: uuid.UUID,
    prompt_modifier: str | None = Form(None),
    new_seed: str | None = Form(None),
    csrf_token: str | None = Form(None),
) -> Response:
    verify_csrf_token(request, csrf_token)
    services = getattr(request.app.state, "services", None)
    settings = getattr(services, "settings", None) if services else None
    pool = getattr(services, "pool", None) if services else None
    secret = getattr(settings, "fastapi_arthor_shared_secret", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="database_unavailable")
    if not secret:
        raise HTTPException(status_code=503, detail="hmac_secret_unset")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, agent_run_id, metadata, status
            FROM external_media_assets
            WHERE id = $1
            """,
            asset_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="unknown_asset_id")
    if str(row["status"]) != "uploaded":
        raise HTTPException(status_code=400, detail="asset_must_be_uploaded")
    meta = _metadata_as_dict(row["metadata"])
    slot_id = meta.get("slot_id")
    if not slot_id:
        raise HTTPException(status_code=400, detail="asset_missing_slot_id")

    mod_raw = (prompt_modifier or "").strip()
    mod_eff = mod_raw if mod_raw else None
    seed_eff: int | None
    if new_seed is None or str(new_seed).strip() == "":
        seed_eff = None
    else:
        try:
            seed_eff = int(str(new_seed).strip())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid_new_seed") from exc

    payload_obj: dict[str, Any] = {"asset_id": str(asset_id)}
    if mod_eff is not None:
        payload_obj["new_prompt_modifier"] = mod_eff
    if seed_eff is not None:
        payload_obj["new_seed"] = seed_eff

    raw = json.dumps(payload_obj, sort_keys=True).encode("utf-8")
    outbound_headers = {
        "Content-Type": "application/json",
        **sign_outbound(secret, raw),
    }
    api_base = _inspector_internal_api_base()
    async with inspector_http_client(api_base) as client:
        api_resp = await client.post(
            "/images/regenerate-slot",
            content=raw,
            headers=outbound_headers,
        )
    if api_resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"regenerate_slot_failed:{api_resp.status_code}",
        )
    data = api_resp.json()
    msg = (
        f"Accepted regeneration — run {data.get('agent_run_id')}, "
        f"asset {data.get('new_asset_id')}"
    )
    ctx = {
        "slot_key": _slot_key(str(slot_id)),
        "slot_id": str(slot_id),
        "asset_id": asset_id,
        "run_id": row["agent_run_id"],
        "regen_message": msg,
        "soft_deleted": False,
    }
    return _render_partial(request, "slot_prompt_modifier.html", ctx)


@_protected.post("/assets/{asset_id}/unsupersede")
async def inspector_unsupersede(
    request: Request,
    asset_id: uuid.UUID,
    csrf_token: str | None = Form(None),
) -> Response:
    verify_csrf_token(request, csrf_token)
    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None
    if pool is None:
        raise HTTPException(status_code=503, detail="database_unavailable")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT metadata, agent_run_id FROM external_media_assets WHERE id = $1",
            asset_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="unknown_asset_id")
    meta = _metadata_as_dict(row["metadata"])
    slot_raw = meta.get("slot_id")
    if not slot_raw:
        raise HTTPException(status_code=400, detail="asset_missing_slot_id")
    anchor_run_id = row["agent_run_id"]

    try:
        await unsupersede_asset(pool, asset_id=asset_id)
    except UnsupersedeUnavailable as exc:
        raise HTTPException(
            status_code=400, detail="unsupersede_unavailable"
        ) from exc

    rows = await queries.fetch_slot_variants(
        pool, slot_id=str(slot_raw), anchor_run_id=anchor_run_id
    )
    variants = [_variant_dict(r) for r in rows]
    return _render_partial(
        request,
        "variants_grid.html",
        {"variants": variants},
    )


_HERO_AB_SCHEMA_HELP = """{
  "site_id": "uuid",
  "idempotency_key": "string (min 8)",
  "business": { "site_name", "industry", "icp_summary", "value_prop", ... },
  "location": { "mode": "local|national|remote", "country", "city?", "region?", ... },
  "brand_voice": { "tone", "notes[]", "style_direction", ... },
  "brand_visual": { "palette": { "light"|"dark": { primary, secondary, ... } }, ... },
  "style_profile_hint": { "lighting", "camera_language", "do_not[]", ... },
  "variants": [
    { "tone_angle": "search|story|offer", "headline", "subhead?" },
    ... exactly 3 entries ...
  ],
  "base_seed": 77,
  "hero_viewport": "desktop|mobile",
  "default_provider_hint": "openai_image"
}"""


def _hero_ab_results_context(
    *,
    desktop_run: uuid.UUID | None,
    mobile_run: uuid.UUID | None,
    desktop_body: dict[str, Any] | None,
    mobile_body: dict[str, Any] | None,
    desktop_prompts: list[dict[str, Any]] | None = None,
    mobile_prompts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    def _urls(body: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not body:
            return []
        raw = body.get("urls") or []
        return [u for u in raw if isinstance(u, dict)]

    return {
        "desktop_run": str(desktop_run) if desktop_run else "",
        "mobile_run": str(mobile_run) if mobile_run else "",
        "desktop_status": (desktop_body or {}).get("status"),
        "mobile_status": (mobile_body or {}).get("status"),
        "desktop_error": (desktop_body or {}).get("error"),
        "mobile_error": (mobile_body or {}).get("error"),
        "desktop_urls": _urls(desktop_body),
        "mobile_urls": _urls(mobile_body),
        "desktop_prompts": desktop_prompts or [],
        "mobile_prompts": mobile_prompts or [],
    }


@_protected.get("/hero-ab")
async def hero_ab_page(
    request: Request,
    load_latest: bool = False,
    desktop_run: uuid.UUID | None = None,
    mobile_run: uuid.UUID | None = None,
    poll: bool = False,
    error: str | None = None,
) -> Response:
    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None

    payload_obj: dict[str, Any] | None = None
    if load_latest and pool is not None:
        payload_obj = await hero_ab.fetch_latest_hero_payload(pool)
    if payload_obj is None:
        payload_obj = hero_ab.default_hero_payload()

    payload_text = json.dumps(payload_obj, indent=2, sort_keys=True)

    recent_rows: list[dict[str, Any]] = []
    if pool is not None:
        for rec in await hero_ab.fetch_recent_hero_runs(pool):
            md = rec["metadata"]
            if isinstance(md, str):
                md = json.loads(md)
            vp = md.get("hero_viewport", "desktop") if isinstance(md, dict) else "desktop"
            view_param = "mobile_run" if vp == "mobile" else "desktop_run"
            recent_rows.append(
                {
                    "id": rec["id"],
                    "status": rec["status"],
                    "started_at": rec["started_at"],
                    "cost_cents": rec["cost_cents"],
                    "provider_label": await hero_ab.run_label(pool, rec["id"]),
                    "view_param": view_param,
                }
            )

    desktop_body: dict[str, Any] | None = None
    mobile_body: dict[str, Any] | None = None
    desktop_prompts: list[dict[str, Any]] = []
    mobile_prompts: list[dict[str, Any]] = []
    settings = services.settings if services else None
    if pool is not None and settings is not None:
        if desktop_run is not None:
            desktop_body = await hero_ab.poll_hero_run(pool, desktop_run, settings)
            desktop_prompts = await hero_ab.fetch_run_provider_prompts(pool, desktop_run)
        if mobile_run is not None:
            mobile_body = await hero_ab.poll_hero_run(pool, mobile_run, settings)
            mobile_prompts = await hero_ab.fetch_run_provider_prompts(pool, mobile_run)

    results_ctx = _hero_ab_results_context(
        desktop_run=desktop_run,
        mobile_run=mobile_run,
        desktop_body=desktop_body,
        mobile_body=mobile_body,
        desktop_prompts=desktop_prompts,
        mobile_prompts=mobile_prompts,
    )
    poll_active = poll and hero_ab.ab_session_needs_polling(
        desktop_run=results_ctx["desktop_run"] or None,
        mobile_run=results_ctx["mobile_run"] or None,
        desktop_status=results_ctx["desktop_status"],
        mobile_status=results_ctx["mobile_status"],
    )
    polling_note = hero_ab.polling_status_note(
        desktop_run=results_ctx["desktop_run"] or None,
        mobile_run=results_ctx["mobile_run"] or None,
        desktop_status=results_ctx["desktop_status"],
        mobile_status=results_ctx["mobile_status"],
    )
    openai_label = hero_ab.openai_model_label(settings) if settings else "OpenAI"
    desktop_arm_title = hero_ab.viewport_arm_title("desktop", settings) if settings else "Desktop header"
    mobile_arm_title = hero_ab.viewport_arm_title("mobile", settings) if settings else "Mobile header"

    return _render(
        request,
        "hero_ab.html",
        {
            "payload_text": payload_text,
            "recent_runs": recent_rows,
            "schema_help": _HERO_AB_SCHEMA_HELP,
            "image_model_costs": format_cost_table_markdown(),
            "error": error,
            "poll_active": poll_active,
            "polling_note": polling_note,
            "openai_label": openai_label,
            "desktop_arm_title": desktop_arm_title,
            "mobile_arm_title": mobile_arm_title,
            **results_ctx,
        },
    )


@_protected.get("/hero-ab/poll")
async def hero_ab_poll(
    request: Request,
    desktop_run: uuid.UUID | None = None,
    mobile_run: uuid.UUID | None = None,
) -> Response:
    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None
    settings = getattr(services, "settings", None) if services else None
    if pool is None or settings is None:
        raise HTTPException(status_code=503, detail="database_unavailable")

    desktop_body = (
        await hero_ab.poll_hero_run(pool, desktop_run, settings)
        if desktop_run is not None
        else None
    )
    mobile_body = (
        await hero_ab.poll_hero_run(pool, mobile_run, settings)
        if mobile_run is not None
        else None
    )
    desktop_prompts = (
        await hero_ab.fetch_run_provider_prompts(pool, desktop_run)
        if desktop_run is not None
        else []
    )
    mobile_prompts = (
        await hero_ab.fetch_run_provider_prompts(pool, mobile_run)
        if mobile_run is not None
        else []
    )
    ctx = _hero_ab_results_context(
        desktop_run=desktop_run,
        mobile_run=mobile_run,
        desktop_body=desktop_body,
        mobile_body=mobile_body,
        desktop_prompts=desktop_prompts,
        mobile_prompts=mobile_prompts,
    )
    ctx["poll_done"] = not hero_ab.ab_session_needs_polling(
        desktop_run=ctx["desktop_run"] or None,
        mobile_run=ctx["mobile_run"] or None,
        desktop_status=ctx["desktop_status"],
        mobile_status=ctx["mobile_status"],
    )
    ctx["polling_note"] = hero_ab.polling_status_note(
        desktop_run=ctx["desktop_run"] or None,
        mobile_run=ctx["mobile_run"] or None,
        desktop_status=ctx["desktop_status"],
        mobile_status=ctx["mobile_status"],
    )
    ctx["desktop_arm_title"] = hero_ab.viewport_arm_title("desktop", settings)
    ctx["mobile_arm_title"] = hero_ab.viewport_arm_title("mobile", settings)
    return _render_partial(request, "hero_ab_results.html", ctx)


@_protected.post("/hero-ab/launch")
async def hero_ab_launch(
    request: Request,
    payload_json: str = Form(...),
    mode: str = Form(...),
    csrf_token: str | None = Form(None),
) -> Response:
    verify_csrf_token(request, csrf_token)
    services = getattr(request.app.state, "services", None)
    settings = getattr(services, "settings", None) if services else None
    secret = getattr(settings, "fastapi_arthor_shared_secret", None)
    if not secret:
        raise HTTPException(status_code=503, detail="hmac_secret_unset")

    base, err = hero_ab.parse_payload_json(payload_json)
    if base is None:
        return await hero_ab_page(request, error=err or "invalid payload")

    viewports: list[str]
    if mode == "both":
        viewports = ["desktop", "mobile"]
    elif mode in ("desktop", "mobile"):
        viewports = [mode]
    else:
        return await hero_ab_page(request, error=f"unknown mode: {mode}")

    api_base = _inspector_internal_api_base()
    launched: dict[str, uuid.UUID] = {}

    async with inspector_http_client(api_base) as client:
        for viewport in viewports:
            body_obj = hero_ab.payload_for_viewport(base, viewport)  # type: ignore[arg-type]
            raw = hero_ab.encode_signed_body(body_obj)
            headers = {
                "Content-Type": "application/json",
                **sign_outbound(secret, raw),
            }
            api_resp = await client.post(
                "/images/hero-candidates/generate",
                content=raw,
                headers=headers,
                timeout=60.0,
            )
            if api_resp.status_code not in (200, 202):
                return await hero_ab_page(
                    request,
                    error=f"{viewport} launch failed ({api_resp.status_code}): {api_resp.text[:200]}",
                )
            data = api_resp.json()
            launched[viewport] = uuid.UUID(str(data["agent_run_id"]))

    desktop_id = launched.get("desktop")
    mobile_id = launched.get("mobile")
    q = "poll=1"
    if desktop_id:
        q += f"&desktop_run={desktop_id}"
    if mobile_id:
        q += f"&mobile_run={mobile_id}"
    return RedirectResponse(url=f"/inspector/hero-ab?{q}", status_code=303)


@_protected.post("/assets/{asset_id}/soft-delete")
async def inspector_soft_delete(
    request: Request,
    asset_id: uuid.UUID,
    reason: str | None = Form(None),
    csrf_token: str | None = Form(None),
) -> Response:
    verify_csrf_token(request, csrf_token)
    if reason is None or not str(reason).strip():
        raise HTTPException(status_code=400, detail="reason_required")

    services = getattr(request.app.state, "services", None)
    pool = getattr(services, "pool", None) if services else None
    if pool is None:
        raise HTTPException(status_code=503, detail="database_unavailable")

    reason_s = str(reason).strip()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE external_media_assets
            SET status = 'superseded',
                metadata = metadata || jsonb_build_object(
                    'soft_deleted', true,
                    'soft_delete_reason', $2::text
                ),
                updated_at = now()
            WHERE id = $1
              AND status = 'uploaded'
            RETURNING metadata, agent_run_id
            """,
            asset_id,
            reason_s,
        )

    if row is None:
        raise HTTPException(status_code=400, detail="soft_delete_unavailable")

    meta = _metadata_as_dict(row["metadata"])
    slot_raw = meta.get("slot_id")
    slot_s = str(slot_raw) if slot_raw else "unknown"
    ctx = {
        "slot_key": _slot_key(slot_s),
        "slot_id": slot_s,
        "asset_id": asset_id,
        "run_id": row["agent_run_id"],
        "regen_message": None,
        "soft_deleted": True,
    }
    return _render_partial(request, "slot_prompt_modifier.html", ctx)


router = APIRouter()
router.include_router(_public)
router.include_router(_protected)
