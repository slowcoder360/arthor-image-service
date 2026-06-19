# Asset pack — consumer contract (arthor-ai)

- **Audience:** arthor-ai `RunImagePack` / site-build stage
- **Date:** 2026-06-13
- **Related:** [`adr/0010-payload-contract-v1.md`](adr/0010-payload-contract-v1.md), [`docs/payload-schema.v1.json`](../docs/payload-schema.v1.json), [`adr/0012-hero-openai-only-and-visual-strategy.md`](adr/0012-hero-openai-only-and-visual-strategy.md)
- **Runtime authority:** [`app/routes/asset_pack.py`](../app/routes/asset_pack.py), [`app/orchestration/pack_worker.py`](../app/orchestration/pack_worker.py), [`app/payload/models.py`](../app/payload/models.py)

---

## Summary

One **PayloadV1** request generates all pack slots (hero + section/card/og/portrait/background). Worker runs **hero first**, then remaining slots (optionally conditioned on hero bytes). Completion is **callback POST** to `callback_url` (not poll-only).

---

## Flow

```
1. POST /images/asset-pack/generate  (PayloadV1 + idempotency_key)
   → 202 { agent_run_id, status: "accepted" }
2. Worker: resolve StyleProfile once → generate slots in order
3. POST callback_url (HMAC signed) with assets[] + pack status
4. Optional: POST /images/regenerate-slot for single-slot fork
5. Optional: POST /images/style-profile/preview for sync probe
```

---

## `POST /images/asset-pack/generate`

| | |
|---|---|
| **Auth** | HMAC over raw JSON body |
| **Body** | Full **PayloadV1** — see ADR-0010 + JSON Schema |
| **First success** | `202` `{ "agent_run_id": "<uuid>", "status": "accepted" }` |
| **Idempotent replay** | `200` `{ "agent_run_id", "status", "idempotent_replay": true }` — same `idempotency_key` |
| **Validation failure** | `400` `{ "errors", "warnings", "completeness_score" }` |
| **Errors** | `401`, `503` database unavailable |

**Required for MVP validation:** see ADR-0010 § minimum-viable payload. Emit `payload_completeness_score` from validator warnings in dev.

---

## Payload highlights (consumer emit checklist)

### Must set correctly

| Area | Field | Notes |
|------|-------|-------|
| Top | `payload_version: "1.0"`, `idempotency_key`, `site_id`, `callback_url` | |
| Pack | `pack.reference_policy.hero_slot_id` | Must match a slot_id |
| Pack | `pack.slot_order` | Hero id first recommended |
| Pack | `pack.default_provider_hint` | `"openai_image"` for OpenAI-native non-hero serializer path |
| Slots | `slot_kind` | `hero`, `section_accent`, `card`, `og`, `portrait`, `background` |
| Slots | `layout.dimensions` | OpenAI heroes in pack: use supported sizes (see hero doc) |
| Slots | `condition_on_slot_id` | Non-hero slots referencing hero when policy enabled |

### `brand_visual.customer_reference_assets` (user uploads)

See [`ASSET-ANALYZE-CONSUMER.md`](ASSET-ANALYZE-CONSUMER.md) for ingest. On pack request:

```jsonc
"customer_reference_assets": [
  {
    "asset_id": "ref-team-1",
    "role": "team",
    "url": "https://…",
    "palette_hex": ["#AABBCC"],
    "usage_hint": "headshot",
    "likeness_consent": true
  }
]
```

| Field | Required | Notes |
|-------|----------|-------|
| `role` | yes | `interior` \| `team` \| `product` \| `logo` \| `ambient` |
| `likeness_consent` | team edits | **`true` required** for OpenAI edit on `team` refs |
| `url` | yes | Fetched at generation when edit/condition path uses ref |

**Pack reference policy:**

```jsonc
"reference_policy": {
  "hero_slot_id": "hero",
  "condition_non_hero_slots_on_hero": true,
  "allow_user_reference_conditioning": true
}
```

When `allow_user_reference_conditioning` is true, user ref bytes may be passed to hero slot generation and to non-hero slots with `condition_on_slot_id` set to hero. Run metadata may include `reference_plan` (same shape as hero — see below).

### Illustrated register (v1)

When `brand_visual.register_default === "illustrated"`:

- **`card` slots** use illustrated OpenAI prompt serializer (flat vector-like; not photorealistic).
- Other slot kinds still use photographic pack serializer unless you set register on resolved profile per slot in future versions.
- Emit clear `style_profile_hint.do_not: ["photorealistic"]` for illustrated packs.

---

## Provider routing (per slot)

Resolution order in worker:

1. `pack.default_provider_hint` if set
2. else `slot.provider_hint`
3. else `og` → `openai_image`
4. else `google_nano_banana`

**Prompt path:**

| Condition | Prompt builder |
|-----------|----------------|
| `slot_kind === "hero"` | Legacy [`build_slot_prompt`](../app/style/prompts.py) |
| non-hero + `openai_image` | [`build_pack_openai_prompt`](../app/style/pack_openai_serializer.py) — industry-aware photorealistic |
| non-hero + illustrated register + `card` | [`serialize_openai_illustration_prompt`](../app/style/illustration_serializer.py) |

Hero **candidates** triad forces OpenAI separately; pack hero slot follows pack worker routing above.

---

## Completion callback

Image-service POSTs to **`payload.callback_url`** when the worker finishes.

| | |
|---|---|
| **Auth** | `X-Arthor-Signature` over JSON body (`sort_keys=True` canonical encoding) |
| **Method** | POST |
| **Expected handler** | arthor-ai e.g. `POST /api/integrations/arthor/image-pack-completed` |

### Callback body

```jsonc
{
  "agent_run_id": "uuid",
  "site_id": "uuid",
  "status": "complete",           // "complete" | "partial" | "failed"
  "assets": [
    {
      "slot_id": "hero",
      "asset_id": "uuid",
      "status": "uploaded"          // or "failed"
    }
  ],
  "total_cost_cents": 42,
  "duration_seconds": 18.5
}
```

| `status` | Meaning |
|----------|---------|
| `complete` | All slots uploaded |
| `partial` | Mix of uploaded and failed |
| `failed` | Zero uploads |

**Implement idempotent callback handler** — retries may duplicate POST; key on `agent_run_id`.

Failed slots still appear in `assets[]` with `"status": "failed"`. Fetch URLs from your DB / R2 via `asset_id` when status is `uploaded`.

---

## `reference_plan` (run metadata)

When `customer_reference_assets` non-empty, worker may attach to run metadata (same semantics as hero):

```jsonc
{
  "reference_plan_version": "1.0",
  "authenticity_mode": "likeness_anchored | space_anchored | stylized",
  "edit_enabled": true,
  "edit_asset_id": "ref-team-1",
  "edit_path": "openai_edit",
  "provider_uses_first_ref_only": true,
  "assets": [ … ],
  "warnings": []
}
```

Only **first eligible** ref is used for OpenAI edit today.

---

## `POST /images/regenerate-slot`

Fork one slot without re-running the full pack.

```jsonc
{
  "asset_id": "uuid",              // uploaded asset to supersede
  "new_seed": 43,                  // optional; default prior + 1
  "new_prompt_modifier": "warmer"  // optional; appended to slot intent
}
```

| Success | `202` `{ "agent_run_id", "new_asset_id", "status": "accepted" }` |
| Notes | **No idempotency** in v1 — each call creates new run. **No pack callback** on regenerate. |

---

## `POST /images/style-profile/preview`

Synchronous single-image probe for style resolution (before full pack). Same PayloadV1 validation + HMAC. Returns preview URL in response body when successful — use for builder “does this style look right?” without full pack cost. See route module for current response fields.

---

## Slot ordering

Worker order:

1. `pack.reference_policy.hero_slot_id` (if present)
2. Remaining ids in `pack.slot_order`
3. Any slots not yet listed

Non-hero slots with `condition_on_slot_id === hero_slot_id` receive hero image bytes as reference when provider supports it and policy allows.

---

## Palette QA

Post-generation palette drift is flagged in asset `metadata.palette_drift` — does not fail the run. Surface in builder QA UI.

---

## TypeScript entrypoint sketch

```typescript
// site-build stage
const payload: PayloadV1 = buildFromSiteSpec(site, assetPackPlanFromSeo);
const res = await signedPost("/images/asset-pack/generate", payload);
// res.status === 202 → wait for callback on /api/integrations/arthor/image-pack-completed
```

Generate JSON Schema types from [`docs/payload-schema.v1.json`](../docs/payload-schema.v1.json) in CI.

---

## Testing

- Fixture: [`tests/test_asset_pack_e2e.py`](../tests/test_asset_pack_e2e.py) `_minimal_pack_payload()`
- Operator smoke: [`agent-control/dev-launch-ledger.md`](../agent-control/dev-launch-ledger.md) § U8

---

## Out of scope

- Hero triad narrow contract — [`HERO-CANDIDATES-CONSUMER.md`](HERO-CANDIDATES-CONSUMER.md)
- Analyze / placement — other consumer docs
- Poll-only pack status API — use callback + `agent_runs` in shared DB when W11 absorbed
