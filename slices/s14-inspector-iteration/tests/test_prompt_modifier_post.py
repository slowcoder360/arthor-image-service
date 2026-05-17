"""s14 AC-2: POST /inspector/slots/{asset_id}/regenerate with valid form+CSRF
returns 200 + HTMX partial. The internal call to /images/regenerate-slot
carries the prompt_modifier and new_seed.
"""

from __future__ import annotations

import os

import pytest

from _s14_db_helpers import cleanup_run, make_pool, seed_uploaded_asset


@pytest.mark.requires_db
@pytest.mark.asyncio
async def test_prompt_modifier_post_invokes_regenerate(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FASTAPI_ARTHOR_SHARED_SECRET", "k")
    monkeypatch.setenv("INSPECTOR_ADMIN_TOKEN", "secret-admin-token")
    monkeypatch.setenv("DATABASE_URL", os.environ["DATABASE_URL"])
    try:
        from app.inspector import router as inspector_router_mod  # type: ignore[import-not-found]
        from app.main import app  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-2: app + inspector.router must be importable ({exc})")
    try:
        from httpx import ASGITransport, AsyncClient
    except ImportError as exc:
        pytest.fail(f"httpx not installed: {exc}")

    pool = await make_pool()
    run_id = None
    asset_id = None
    captured = {}
    try:
        async with pool.acquire() as conn:
            run_id, asset_id = await seed_uploaded_asset(conn)

        class FakeClient:
            async def post(self, url, content=None, headers=None, **kw):
                captured["url"] = url
                captured["body"] = content
                captured["headers"] = headers or {}

                class _R:
                    status_code = 202

                    def json(self_):
                        import uuid as _uuid
                        return {
                            "agent_run_id": str(_uuid.uuid4()),
                            "new_asset_id": str(_uuid.uuid4()),
                            "status": "accepted",
                        }

                return _R()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        monkeypatch.setattr(
            inspector_router_mod,
            "inspector_http_client",
            lambda *a, **kw: FakeClient(),
            raising=False,
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            get_login = await client.get("/inspector/login")
            csrf = get_login.cookies.get("arthor_csrf_token") or ""
            client.cookies.set("arthor_csrf_token", csrf)

            resp = await client.post(
                f"/inspector/slots/{asset_id}/regenerate",
                data={
                    "prompt_modifier": "with neon accents",
                    "new_seed": "7",
                    "csrf_token": csrf,
                },
                headers={
                    "Authorization": "Bearer secret-admin-token",
                    "HX-Request": "true",
                },
            )

        assert resp.status_code == 200, (
            f"AC-2: POST with valid CSRF must 200 (HTMX partial); "
            f"got {resp.status_code} {resp.text[:200]!r}"
        )
        assert "url" in captured, (
            "AC-2: route must call the regenerate-slot endpoint via the inspector HTTP client"
        )
        body_str = (
            captured["body"].decode() if isinstance(captured["body"], (bytes, bytearray)) else str(captured["body"])
        )
        assert "with neon accents" in body_str, (
            "AC-2: outbound regenerate body must carry the prompt_modifier text"
        )
        assert '"new_seed": 7' in body_str or '"new_seed":7' in body_str, (
            "AC-2: outbound regenerate body must carry new_seed=7"
        )
    finally:
        async with pool.acquire() as conn:
            if run_id is not None:
                await cleanup_run(conn, run_id)
        await pool.close()
