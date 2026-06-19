# Cross-repo handoff index — image-service → consumers

- **Date:** 2026-06-13
- **Implementation branch:** `pod/u-completion-wave` (U1–U8)
- **Shared secret:** `FASTAPI_ARTHOR_SHARED_SECRET` (HMAC on all `/images/*` traffic)
- **Domain language:** [`plan/CONTEXT.md`](CONTEXT.md)

This index is the **single entry point** for other repos building against image-service. Read the doc for your role first; then the payload ADRs as needed.

---

## By consumer repo

| Repo | Role | Read first | Then |
|------|------|------------|------|
| **arthor-ai** | Site build, hero triad, asset pack, web upload analyze | [`ASSET-PACK-CONSUMER.md`](ASSET-PACK-CONSUMER.md) | [`HERO-CANDIDATES-CONSUMER.md`](HERO-CANDIDATES-CONSUMER.md), [`ASSET-ANALYZE-CONSUMER.md`](ASSET-ANALYZE-CONSUMER.md), [`adr/0010-payload-contract-v1.md`](adr/0010-payload-contract-v1.md), [`docs/payload-schema.v1.json`](../docs/payload-schema.v1.json) |
| **arthor-agent** | SMS/email ingest, chat confirm, preview links | [`AGENT-MEDIA-CONSUMER.md`](AGENT-MEDIA-CONSUMER.md) | [`ASSET-ANALYZE-CONSUMER.md`](ASSET-ANALYZE-CONSUMER.md) |
| **template-repo / Cursor** | Place logo URLs in layout slots | [`PLACEMENTS-CONSUMER.md`](PLACEMENTS-CONSUMER.md) | (reads from arthor-ai site state — not image-service directly) |
| **seo-service** | Pack slot plan | Already on seo `main` — `asset_pack_plan` | [`adr/0010-payload-contract-v1.md`](adr/0010-payload-contract-v1.md) for emitted pack shape |

---

## By capability

| Capability | Consumer doc | Endpoint(s) |
|------------|--------------|-------------|
| User upload analyze | [`ASSET-ANALYZE-CONSUMER.md`](ASSET-ANALYZE-CONSUMER.md) | `POST /images/assets/analyze` |
| Logo placement manifest | [`PLACEMENTS-CONSUMER.md`](PLACEMENTS-CONSUMER.md) | `GET /images/placements/{site_id}` (optional; prefer site state) |
| Full asset pack | [`ASSET-PACK-CONSUMER.md`](ASSET-PACK-CONSUMER.md) | `POST /images/asset-pack/generate` + callback |
| Hero triad | [`HERO-CANDIDATES-CONSUMER.md`](HERO-CANDIDATES-CONSUMER.md) | `POST/GET /images/hero-candidates/*` |
| Slot regenerate | [`ASSET-PACK-CONSUMER.md`](ASSET-PACK-CONSUMER.md) § Regenerate | `POST /images/regenerate-slot` |
| Style probe | [`ASSET-PACK-CONSUMER.md`](ASSET-PACK-CONSUMER.md) § Style preview | `POST /images/style-profile/preview` |

---

## Auth (all consumers)

See [`adr/0006-hmac-auth-convention.md`](adr/0006-hmac-auth-convention.md).

| Direction | Header | Body signed |
|-----------|--------|-------------|
| Inbound to image-service | `X-Arthor-Signature: sha256=<hex>` | Raw JSON bytes (empty for GET poll/placements) |
| Outbound callback (pack) | Same | Canonical JSON (`sort_keys=True`) POST body |

Python: `app.auth.hmac.sign_body(secret, body)` — mirror in TypeScript on arthor-ai side.

---

## Product defaults (locked — do not re-debate in consumers)

1. **Default auto:** When analyze `confidence ≥ 0.75` and `confirm_first_required === false`, upstream applies `recommended_treatment` without asking.
2. **Confirm-first exception:** Low confidence, likeness/face-in-hero risk, ambiguous logo vs photo → max 3 chips; image-service sets `confirm_first_required`.
3. **Image-service never owns chat/SMS UX** — only analyze + treatment fields.
4. **Heroes:** OpenAI only ([`adr/0012-hero-openai-only-and-visual-strategy.md`](adr/0012-hero-openai-only-and-visual-strategy.md)).
5. **Headlines never in provider prompts** (heroes or pack).

Optional later: `media_confirmation_mode: auto | confirm_first` on user/site profile (**stored in arthor-agent/ai**, not image-service).

---

## Verification (operator)

| Tier | Doc |
|------|-----|
| Hero smoke | [`HANDOFF-W21-H-DEPLOY-SMOKE.md`](HANDOFF-W21-H-DEPLOY-SMOKE.md) |
| Full pack smoke | [`../agent-control/dev-launch-ledger.md`](../agent-control/dev-launch-ledger.md) § U8 |
| Slice pytest | [`../agent-control/slice-status.md`](../agent-control/slice-status.md) |

---

## Update log

- **2026-06-13** — Initial cross-repo index after U1–U8 completion wave.
