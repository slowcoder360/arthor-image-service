"""Deterministic hero post-generation QA gate tests."""

from __future__ import annotations

import io

import pytest
from PIL import Image, ImageDraw

from app.quality.hero_failure_modes import FAILURE_MODES, pick_primary_failure_mode
from app.quality.hero_post_checks import (
    AUTO_RETRY_FAILURE_MODES,
    hero_post_check_failure_mode,
    run_hero_post_checks,
)

_DESKTOP_SIZE = (1536, 1024)


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _clean_hero_png() -> bytes:
    """Soft scene: quiet left/top copy zones, moderate detail center-right."""
    w, h = _DESKTOP_SIZE
    img = Image.new("RGB", (w, h), (210, 205, 198))
    draw = ImageDraw.Draw(img)
    inset_w = int(w * 0.40)
    top_h = int(h * 0.14)
    draw.rectangle((0, 0, inset_w, h), fill=(218, 214, 208))
    draw.rectangle((0, 0, w, top_h), fill=(220, 216, 210))
    cx0, cy0 = int(w * 0.55), int(h * 0.25)
    cx1, cy1 = int(w * 0.82), int(h * 0.78)
    draw.ellipse((cx0, cy0, cx1, cy1), fill=(165, 140, 120))
    draw.rectangle((cx0 + 40, cy0 + 80, cx1 - 30, cy1 - 40), fill=(140, 115, 95))
    return _png_bytes(img)


def _rendered_text_png() -> bytes:
    w, h = _DESKTOP_SIZE
    img = Image.new("RGB", (w, h), (230, 228, 224))
    draw = ImageDraw.Draw(img)
    inset_w = int(w * 0.38)
    top_h = int(h * 0.14)
    for y in range(top_h + 30, h - 40, 28):
        draw.line((24, y, inset_w - 24, y), fill=(10, 10, 10), width=3)
    return _png_bytes(img)


def _rendered_ui_png() -> bytes:
    w, h = _DESKTOP_SIZE
    img = Image.new("RGB", (w, h), (200, 198, 194))
    draw = ImageDraw.Draw(img)
    top_h = int(h * 0.14)
    for x in range(20, w - 20, 90):
        draw.rectangle((x, 12, x + 70, top_h - 12), outline=(5, 5, 5), width=2)
        draw.line((x + 8, top_h // 2, x + 62, top_h // 2), fill=(0, 0, 0), width=2)
    return _png_bytes(img)


def _safe_zone_violation_png() -> bytes:
    w, h = _DESKTOP_SIZE
    img = Image.new("RGB", (w, h), (128, 128, 128))
    draw = ImageDraw.Draw(img)
    inset_w = int(w * 0.40)
    top_h = int(h * 0.14)
    for y in range(top_h, h, 6):
        shade = 80 + (y % 40)
        draw.line((0, y, inset_w, y), fill=(shade, shade - 10, shade + 5), width=2)
    cx0, cy0 = int(w * 0.55), int(h * 0.30)
    cx1, cy1 = int(w * 0.80), int(h * 0.75)
    for y in range(cy0, cy1, 6):
        shade = 90 + (y % 35)
        draw.line((cx0, y, cx1, y), fill=(shade, shade - 8, shade + 8), width=2)
    return _png_bytes(img)


def test_clean_hero_passes_post_checks():
    modes = run_hero_post_checks(_clean_hero_png(), viewport="desktop", safe_area_inset_pct=40)
    assert modes == []


def test_rendered_text_detected():
    modes = run_hero_post_checks(_rendered_text_png(), viewport="desktop", safe_area_inset_pct=40)
    assert "rendered_text" in modes


def test_rendered_ui_detected():
    modes = run_hero_post_checks(_rendered_ui_png(), viewport="desktop", safe_area_inset_pct=40)
    assert "rendered_ui" in modes


def test_safe_zone_violation_detected():
    modes = run_hero_post_checks(
        _safe_zone_violation_png(),
        viewport="desktop",
        safe_area_inset_pct=40,
    )
    assert "safe_zone_violation" in modes


def test_failure_modes_include_new_labels():
    assert "safe_zone_violation" in FAILURE_MODES
    assert "rendered_text" in FAILURE_MODES


def test_pick_primary_failure_mode_priority():
    assert pick_primary_failure_mode("palette_drift", "rendered_text") == "rendered_text"
    assert pick_primary_failure_mode("safe_zone_violation", "rendered_ui") == "rendered_ui"


def test_auto_retry_modes_subset():
    assert AUTO_RETRY_FAILURE_MODES == frozenset({"rendered_text", "safe_zone_violation"})


def test_hero_post_check_failure_mode_helper():
    assert hero_post_check_failure_mode(["safe_zone_violation", "rendered_text"]) == "rendered_text"
    assert hero_post_check_failure_mode([]) is None


@pytest.mark.asyncio
async def test_poll_surfaces_failure_mode_on_urls(monkeypatch, tmp_path):
    """Uploaded asset metadata failure_mode surfaces in poll urls."""
    import asyncio
    import json
    import uuid

    from httpx import ASGITransport, AsyncClient

    from app.auth.hmac import sign_body
    import app.routes.hero_candidates as hero_routes
    from tests._hero_fake_pool import HeroFakePool, seed_uploaded_hero_assets
    from tests.test_hero_candidates import _build_hero_request, _prepare_app

    pool = HeroFakePool()
    app, _, _ = await _prepare_app(monkeypatch, tmp_path, pool=pool)

    async def _stub_worker(services_arg, *, run_id, request, payload, style_profile):
        seed_uploaded_hero_assets(services_arg.pool.store, run_id, count=3)
        for asset in services_arg.pool.store.assets:
            if asset["agent_run_id"] == run_id and asset["metadata"].get("variant_index") == 0:
                asset["metadata"]["failure_mode"] = "rendered_text"
        row = services_arg.pool.store.agent_runs[run_id]
        row["status"] = "ok"
        row["finished_at"] = "now"

    monkeypatch.setattr(hero_routes, "run_hero_candidates_in_background", _stub_worker)

    payload = _build_hero_request(idem_key=f"hero-qa-{uuid.uuid4()}")
    raw = json.dumps(payload).encode()
    sig = sign_body("k", raw)
    get_sig = sign_body("k", b"")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        post_resp = await client.post(
            "/images/hero-candidates/generate",
            content=raw,
            headers={"X-Arthor-Signature": sig},
        )
        run_id = post_resp.json()["agent_run_id"]
        await asyncio.sleep(0.1)
        poll = await client.get(
            f"/images/hero-candidates/{run_id}",
            headers={"X-Arthor-Signature": get_sig},
        )

    urls = poll.json()["urls"]
    flagged = [u for u in urls if u.get("failure_mode") == "rendered_text"]
    assert len(flagged) == 1
