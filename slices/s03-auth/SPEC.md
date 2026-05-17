---
id: s03-auth
title: HMAC inbound verify + INSPECTOR_ADMIN_TOKEN bearer + outbound signer for callbacks
depends_on: [s01-skeleton]
parallel_safe: true
estimated_loc: 250
---

# s03-auth — HMAC verify + admin token + outbound signer

## Summary

Ship the auth primitives. Inbound HMAC verification for arthor-ai → this service (`X-Arthor-Signature: sha256=<hex>` over raw body, per ADR-0006). A separate Bearer middleware for `/inspector/*` driven by `INSPECTOR_ADMIN_TOKEN` (also accepts a cookie). An outbound signer used by `app/callback/client.py` (s10) to sign callbacks to arthor-ai. No routes mounted in this slice — middleware is exported and used by downstream slices.

## Acceptance criteria

- AC-1: `app/auth/hmac.py` exports `sign_body(secret: str, body: bytes) -> str` that returns `f"sha256={hex_digest}"` using `hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()`.
- AC-2: `app/auth/hmac.py` exports `verify_signature(secret: str, body: bytes, header_value: str | None) -> bool` using `hmac.compare_digest`. Returns `False` when `header_value is None`, when the prefix is not `sha256=`, or when the digests differ. Constant-time compare even on prefix mismatch (decode after early-return).
- AC-3: `app/auth/hmac.py` exports an ASGI middleware-style helper `async def require_hmac(request: Request) -> bytes`: reads the body once (caches in `request.state.raw_body`), looks up `settings.fastapi_arthor_shared_secret` via `request.app.state.services.settings`; raises `HTTPException(503, detail="hmac_secret_unset")` if secret unset; raises `HTTPException(401, detail="invalid_signature")` on mismatch; raises `HTTPException(400, detail="empty_body")` on empty body. Returns the raw body bytes.
- AC-4: `app/auth/inspector_token.py` exports `async def require_inspector_token(request: Request) -> None`: accepts `Authorization: Bearer <token>` header OR `arthor_inspector_token` cookie. 503 when `settings.inspector_admin_token` unset; 401 on mismatch. Constant-time compare.
- AC-5: `app/auth/inspector_token.py` exports `def issue_inspector_cookie(response: Response, token: str) -> None`: sets cookie `arthor_inspector_token` with `httponly=True, secure=True, samesite="strict"`, max_age=86400.
- AC-6: `app/auth/sign.py` exports `def sign_outbound(secret: str, body: bytes) -> dict[str, str]` returning `{"X-Arthor-Signature": sign_body(secret, body)}`. Identical algorithm to inbound — round-trip tested.
- AC-7: All three modules ship `__all__` with their public surface and zero side effects at import time.

## Paths in scope

- `app/auth/__init__.py`
- `app/auth/hmac.py`
- `app/auth/inspector_token.py`
- `app/auth/sign.py`

## Paths out of scope (do not touch)

- `app/main.py` — middleware is NOT mounted in this slice; s10 (asset-pack endpoint) and s13 (inspector) wire the middleware where they own the route.
- `app/config.py`, `app/runtime.py` — the env keys are already declared on `Settings` from s01.
- `app/payload/**`, `app/routes/**`, `app/inspector/**`
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`, `db/**`

## Failing tests the subagent must turn green

- `slices/s03-auth/tests/test_sign_body.py` — asserts `sign_body(secret, body)` matches a known-good Python `hmac` reference; asserts prefix is `sha256=`; asserts deterministic for identical inputs; asserts different secrets produce different signatures.
- `slices/s03-auth/tests/test_verify_signature.py` — table-driven: valid sig → True; missing header → False; wrong prefix → False; wrong hex → False; secret swap → False; tampered body → False.
- `slices/s03-auth/tests/test_round_trip.py` — `sign_outbound` output successfully verifies via `verify_signature` against the same secret + body. Verifies against a different body → False.
- `slices/s03-auth/tests/test_require_hmac.py` — mounts a temp FastAPI route guarded by `Depends(require_hmac)` (the only place `Depends` is allowed — for test injection ergonomics); asserts 503 when secret unset, 401 on missing/bad sig, 400 on empty body, 200 on valid sig. Asserts `request.state.raw_body` contains the bytes after pass.
- `slices/s03-auth/tests/test_inspector_token.py` — table-driven: Bearer header valid → pass; cookie valid → pass; both missing → 401; secret unset → 503; constant-time mismatch → 401.
- `slices/s03-auth/tests/test_issue_cookie.py` — asserts cookie has `HttpOnly`, `Secure`, `SameSite=Strict`, the documented max_age.

## Hints

- ADR anchor: [plan/adr/0006-hmac-auth-convention.md](plan/adr/0006-hmac-auth-convention.md).
- Reference implementation in arthor-agent: `~/arthor-agent/communications/auth.py` (HMAC verify pattern) and `~/arthor-agent/app/main.py:273-279` (admin token shape). Match the error shape exactly (FastAPI `HTTPException(status_code, detail=<short_string>)`).
- The middleware functions live in `app/auth/*` and are *imported* by downstream slices' routers. Do not register middleware on `app.middleware(...)` globally in this slice — that would couple `s03-auth` to route-mount decisions owned by `s10`/`s13`.
- ADR-0006 explicitly accepts the no-replay-protection gap. Do not invent timestamps or nonces in v1; document in code comments referencing the ADR.
- Cookie shape per ADR-0006 §"For browser convenience"; CSRF protection on POST is s13's concern, not this slice.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s03-auth/tests` is fully green, no files under `paths_out_of_scope` were modified, and no test files under `slices/s03-auth/tests/` were modified.
