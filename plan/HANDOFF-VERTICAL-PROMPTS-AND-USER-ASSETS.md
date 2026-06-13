# HANDOFF — Vertical hero prompts + user-asset roadmap

- **Audience:** Tier-1 orchestrator + Composer subagents in `~/arthor-image-service`
- **Date:** 2026-06-12
- **Branch:** `main` (hero wave merged; Justin iterates on `main`)
- **Justin lane:** Operator — visual QA in inspector + cohort eval; **do not thrash arthor-ai contract** until prompts stable

---

## Wave goal (this orchestrator)

**Tighten industry-specific hero prompts** so each vertical reads credible (backdrop, job scenes, invariants) — not generic residential / stock slop.

**Not in this wave (defer):**

- arthor-ai hero consumer contract rewrite (`plan/HERO-CANDIDATES-CONSUMER.md`)
- `POST /images/assets/analyze` (user upload classification)
- Asset-pack non-hero slot serializer parity
- Merge to prod / arthor-ai wire-up

---

## Architecture (locked)

| Layer | Owner | Responsibility |
|-------|-------|----------------|
| **Compile + strategy** | image-service (deterministic) | Industry backdrop, tone→job, scene archetype, serializer — **no LLM on hot path** |
| **Generate + edit** | image-service | OpenAI only for heroes (ADR-0012) |
| **Confirm usage with user** | arthor-agent / arthor-ai (later) | **Default: auto-plan + site preview approve.** Optional upfront confirm only when low confidence or high-risk (face/likeness). **Not image-service.** |
| **Plan site slots** | arthor-seo-service | `asset_pack_plan` (W21-P on `main`) |
| **Place URLs** | Cursor / template-repo | Placement-only |

**User uploads (future):** ingest → analyze (deterministic capabilities) → **chat confirms intent** → reference/edit/generate. Image-service never owns conversational UX.

---

## Code map — where vertical prompts live

| File | Role |
|------|------|
| `app/style/hero_archetypes.py` | **`INDUSTRY_CONTEXTS`** — match_keys, backdrop, trust/outcome/experience/authority, feel, avoid_extra |
| `app/style/hero_visual_strategy.py` | Scene archetypes, dental backdrop anchors, authenticity mode |
| `app/style/hero_prompt_compiler.py` | `COMPILER_VERSION` — assembles slot prompts from archetypes + strategy |
| `app/style/hero_openai_prompt_serializer.py` | Model-native brief sent to gpt-image-2 (line-broken English, Invariants not Avoid lists) |
| `app/style/hero_reference_plan.py` | User ref routing (`interior`, `team`, `product`, `logo`, `ambient`) + likeness_consent |
| `app/orchestration/hero_worker.py` | Generate + regenerate-variant + desktop→mobile seed |
| `app/routes/hero_candidates.py` | API surface |
| `app/quality/hero_post_checks.py` | Deterministic QA flags → `failure_mode` on poll |

**Tests (must stay green):**

| File | Purpose |
|------|---------|
| `tests/test_hero_industry_prompts.py` | Prompt **text guards** per vertical (couch/gym/legal-family regressions) |
| `tests/test_hero_prompt_compiler.py` | Compiler version + structure |
| `tests/test_hero_openai_prompt_serializer.py` | Serializer shape |
| `tests/test_hero_candidates.py` | API + worker integration |
| `tests/test_hero_reference_assets.py` | Reference edit path |

**Eval tooling:**

| Tool | Purpose |
|------|---------|
| `scripts/hero_cohort_eval.py` | Batch generate across `COHORT_SCENARIOS`; writes CSV + summary |
| Inspector `/inspector/hero-ab` | Manual A/B + viewport lab |
| Inspector cohort review | `/inspector/cohort-review` — visual pass/fail cards |

---

## Industries in cohort today

Resolved via `resolve_industry()` substring match on `business.industry`:

| Label | match_keys (partial) | Status |
|-------|----------------------|--------|
| `dental` | dental, dentist, orthodont | Justin-approved v3.2 |
| `legal` | legal, law, attorney, lawyer | Active tuning |
| `home_services` | hvac, plumb, electric, contractor, roofing | Active tuning |
| `healthcare` | health, medical, clinic, therapy, chiro, physical therapy | Active tuning |
| `outdoor_services` | landscap, lawn, garden, mow, arbor, tree care, yard | Active tuning |
| `general_services` | fallback when no match | Default backdrop |

Adding a vertical = new `IndustryContext` row + cohort scenario in `hero_cohort_eval.py` + test in `test_hero_industry_prompts.py`.

---

## How to tighten one vertical (subagent recipe)

1. **Reproduce failure** — inspector hero-ab or cohort eval for that industry slug; capture `failure_mode` + prompt in run metadata (`metadata.hero_provider_prompts[]`).
2. **Fix deterministic layer first** — edit `hero_archetypes.py` (backdrop, job scenes, `avoid_extra`); then `hero_visual_strategy.py` if scene archetype wrong.
3. **Serializer last** — only if model-native brief needs rewording; keep `COMPILER_VERSION` bump if prompt hash semantics change.
4. **Add regression test** — assert forbidden tokens appear as **Invariants** in compiled or serialized prompt (see existing tests).
5. **Re-run** — `pytest tests/test_hero_industry_prompts.py tests/test_hero_prompt_compiler.py -q` then optional cohort slice for that slug only.
6. **Justin visual pass** — inspector; do not call vertical done without Justin thumbs-up on at least one triad.

**Do not:**

- Add LLM classification or "pick industry" inference
- Change `HeroCandidatesRequest` / poll JSON without explicit Justin ask
- Weaken global guards in `GLOBAL_HERO_AVOID` or left safe-zone composition rules
- Send marketing headlines to the image provider (copy_metrics / overlay only)

---

## Prompt quality bar (Justin)

- Reads as **photorealistic homepage hero background plate** with human subject when appropriate
- **Industry-readable backdrop** (dental ≠ living room; HVAC ≠ couch leisure; legal ≠ random family at threshold)
- Left copy safe-zone via **soft contrast**, not empty void
- **Invariants** block for negatives; no long Avoid lists in provider text
- OpenAI **quality=high** for hero finals (config default)

Research: `plan/deep-research-report (20).md`

---

## Runtime (local)

```bash
cd ~/arthor-image-service
# DATABASE_URL, R2, OPENAI_*, FASTAPI_ARTHOR_SHARED_SECRET in .env
uvicorn app.main:app --reload --port 8010
```

- Inspector: `http://127.0.0.1:8010/inspector/hero-ab`
- Cohort eval: `python scripts/hero_cohort_eval.py --base-url http://127.0.0.1:8010 --replicates 1`

Restart uvicorn after compiler/serializer edits.

---

## Future path — user photos (context only; not this wave)

**Product default (Justin 2026-06-12):** assume **non-technical users, minimal input, lowest friction.** We do ~99% of the lift. Do **not** default to a classification quiz.

When vertical prompts stable:

1. `POST /images/assets/analyze` — deterministic capabilities (face, blur, logo alpha, aspect) + **confidence-scored** `recommended_treatment`
2. **Auto path (default):** analyze → system applies best treatment when confidence ≥ threshold → generate/place → **site preview link** → user thumbs up/down (or “try different” chips). Chat line: *"Got it — our photo team is placing this on your site. I'll send a preview before anything goes live."*
3. **Confirm-first path (exception):** only when analyze confidence is low **or** high-risk (face in hero, likeness, ambiguous logo vs photo). Then short A/B/C chips — still not open-ended questions.
4. **User preference (optional, once):** *"Want me to ask before I use photos, or just show you in the preview?"* → store `media_confirmation_mode: auto | confirm_first` on user/site profile. Default **`auto`**.
5. Treatments: `enhance_headshot`, `reference` edit, `placement_only` (logo), asset-pack slots
6. **Then** update arthor-ai consumer against `plan/HERO-CANDIDATES-CONSUMER.md`

Channels: SendBlue, email attachment (W22/W23), arthor-ai web upload — same analyze output; UX in chat/builder only.

### Confidence routing (deterministic — no LLM verdict)

| Signal | Auto treatment | Confirm-first? |
|--------|----------------|----------------|
| PNG/SVG + alpha, square-ish | `placement_only` logo | No |
| Face + portrait aspect + blur high | `enhance_headshot` → about/portrait slot | **Yes** if hero composite |
| Face + likeness for hero | `reference` + hero | **Yes** — consent + preview |
| Interior wide shot | `reference` section/hero bg | No if confidence high |
| Ambiguous / multi-face / low res | — | **Yes** — 2–3 chips max |

**Publish gate unchanged:** nothing merges to prod without preview approve (W46). Auto mode skips *intent* interrogation, not *publish* approval.

---

## Done when (this wave)

- [ ] Justin marks each active cohort vertical **visually credible** in inspector (minimum: dental, legal, home_services, healthcare, outdoor_services)
- [ ] `pytest` green on hero test modules listed above
- [ ] Cohort eval summary documents pass rate + remaining `failure_mode` counts per slug
- [ ] `agent-control/dev-launch-ledger.md` updated with last cohort run date + SHA
- [ ] No API contract changes without Justin

---

## ADRs / consumer docs (read-only unless Justin reopens)

- `plan/adr/0012-hero-openai-only-and-visual-strategy.md`
- `plan/HERO-CANDIDATES-CONSUMER.md` — arthor-ai adapter **waits** until this wave closes
- `plan/HANDOFF-HERO-NEXT-AGENT.md` — site-wide + illustration paths after vertical pass

---

## Update log

- **2026-06-12** — Initial handoff: vertical prompt tightening wave + user-asset roadmap context for in-repo orchestrator.
- **2026-06-12** — UX default: auto-plan + preview approve; confirm-first only on low confidence / likeness; optional user `media_confirmation_mode`.
