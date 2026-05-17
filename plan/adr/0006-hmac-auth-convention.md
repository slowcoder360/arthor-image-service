# ADR 0006: HMAC auth convention + admin token

- Status: proposed
- Date: 2026-05-17

## Context

Research subagent #1 documented the existing HMAC convention between arthor-ai and arthor-agent:
- Header: `X-Arthor-Signature: sha256=<hex>`
- Signs: **raw JSON request body only** (no method, no path, no timestamp, no nonce)
- Shared secret env: `FASTAPI_ARTHOR_SHARED_SECRET`
- Verify: constant-time digest compare (`hmac.compare_digest`)
- Errors: 503 (secret unset), 401 (invalid sig), 400 (malformed JSON)
- **No replay protection** — a captured signed body can be re-played indefinitely

Admin/inspector auth in arthor-agent: `Authorization: Bearer <CCS_ADMIN_TOKEN>`. `INSPECTOR_ADMIN_TOKEN` mentioned in arthor-agent's PACKET.md but not implemented anywhere.

## Options considered

- **A. Mirror arthor-agent exactly (no replay protection)** — consistency wins; same code shape; W11 doesn't see a divergent auth surface.
- **B. Extend the convention here with timestamp + nonce + 5-minute window** — better security; but a captured body without timestamp is still trivially replayable until both services adopt the change.
- **C. Use mTLS instead** — adds Cloudflare-level configuration; out of scope for v1.

## Decision

**Option A: mirror arthor-agent exactly for inbound from arthor-ai.** Plus:

- Reuse env-var name `FASTAPI_ARTHOR_SHARED_SECRET` (same secret across the ecosystem).
- Implement a thin `app/auth/hmac.py` with `sign_body(secret, body) -> str` and `verify_signature(secret, body, header_value) -> bool`. Both use `hmac.compare_digest` for timing safety.
- A FastAPI dependency-style middleware (read body once, verify, hand the bytes off to the handler). Keep the body bytes in `request.state.raw_body` so handlers can re-parse without re-reading.
- Sign outbound HTTP callbacks to arthor-ai with the same primitive (`POST /api/integrations/arthor/image-pack-completed`).
- Error model identical to arthor-agent: 503 / 401 / 400, FastAPI `HTTPException` with `detail` field.

For the inspector GUI:

- **New env-var `INSPECTOR_ADMIN_TOKEN`** (greenfield per intake decision G). Bearer in `Authorization` header. Same shape as arthor-agent's `CCS_ADMIN_TOKEN` (constant-time compare). 503 when unset, 401 on mismatch.
- Implemented in `app/auth/admin.py` as a separate middleware mounted only on `/inspector/*` routes.
- For browser convenience, the inspector also accepts the token as a cookie `arthor_inspector_token` set by a `/inspector/login` POST endpoint. Cookie value is the same token; FastAPI handler accepts either header or cookie.

**Replay-protection gap documented as a follow-up issue.** Once Justin or anyone else wants to upgrade, the same upgrade applies to arthor-agent — that's a cross-service change with its own PR. v1 inherits the existing posture.

## Consequences

What gets easier:
- Cross-service HMAC reuse without divergent code paths.
- `INSPECTOR_ADMIN_TOKEN` is cleanly greenfield — no legacy compatibility cost.

What gets harder:
- The replay window is unbounded. If a body leaks (logs, screenshots), an attacker can re-trigger paid provider calls. Mitigation: rate-limit `POST /images/asset-pack/generate` by `idempotency_key` (same idempotency key returns the existing run instead of re-running), and rate-limit by `site_id` + 5-minute window in `app/auth/hmac.py` (Redis if we have one; in-memory dict if not).
- Cookie-based admin auth requires CSRF protection on POST inspector endpoints (form-encoded). Use SameSite=Strict + double-submit token; documented in slice s13.
