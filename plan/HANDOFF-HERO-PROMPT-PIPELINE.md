# Handoff — Hero prompt pipeline + model optimization

> **Superseded for current direction (2026-06-11):** see [`plan/HANDOFF-HERO-VISUAL-STRATEGY.md`](HANDOFF-HERO-VISUAL-STRATEGY.md) and [`plan/adr/0012-hero-openai-only-and-visual-strategy.md`](adr/0012-hero-openai-only-and-visual-strategy.md).

- From: orchestrator session (W21-H hero A/B, deploy smoke, prompt architecture)
- Date: 2026-06-11
- Branch: `pod/w21-h-hero-candidates` (many changes **local/uncommitted**)

## What we're doing

Build a **deterministic, structured** hero-image pipeline for arthor-image-service: compile provider prompts at POST time from business/tone/palette/industry signals (not free-form copy in prompts), pre-store all 3 variant prompts, run a dumb worker that only calls image APIs. Separately, optimize for **Google Nano Banana vs OpenAI GPT Image** using the new deep-research report. User wants a **read-only analysis agent** next to produce an improvement plan — not implementation yet.

## What we've done

### Deploy / ops (W21-H smoke)
- pytest green for `tests/test_hero_candidates.py`
- Local uvicorn on **8010**; HMAC secret must match arthor-ai; restart after secret change
- R2 public URLs fixed (`R2_PUBLIC_URL`, `browser_url_for()`)
- Ledger: `agent-control/dev-launch-ledger.md`

### Hero A/B inspector (mostly uncommitted)
- `/inspector/hero-ab` — edit payload, run Google/OpenAI/both, side-by-side results
- Poll fixes: DB-only refresh, skip completed arms, stale orphan run → `failed`
- Error message surfaced on failed runs in UI

### Prompt / composition learnings (from stored A/B images in `scratch/hero-ab-review/`)
- Google story variant rendered **fake nav bar** — caused by "navigation overlay" wording + headline in prompt
- OpenAI better industry fidelity on `gpt-image-1`; Google drifted to generic spa
- Review doc: `scratch/hero-ab-review/REVIEW.md`

### Models in use today
| Provider key | API model | Config |
|---|---|---|
| `openai_image` | **`gpt-image-1`** | `app/providers/openai_image.py` `DEFAULT_MODEL_VERSION` |
| `google_nano_banana` | **`gemini-2.5-flash-image`** | `app/providers/google_nano_banana.py` |

No env override for model selection. No `quality` param on OpenAI calls.

### NEW: Deterministic prompt compiler (this session, likely uncommitted)
- **`app/style/hero_prompt_compiler.py`** — industry archetypes (dental, legal, home_services, healthcare, default), stacks palette/feel/lighting/overlay, **no headline text in provider prompt**
- **`POST /images/hero-candidates/generate`** — `finalize_hero_triad_prompts()` at accept time → stores `metadata.hero_provider_prompts[]` on run
- **`app/orchestration/hero_worker.py`** — loads precompiled prompts from run metadata; worker is image-only
- **`app/style/prompt_improver.py`** — optional LLM rewrite after compile; **`hero_prompt_improve_enabled=False` by default**
- **`app/providers/image_model_costs.py`** — cost reference table; shown on `/inspector/hero-ab`
- Cost table extended for `gpt-image-1.5`, `gpt-image-2` in `openai_image.py` (not default yet)
- Tests: `tests/test_hero_prompt_compiler.py` + existing hero tests pass (9)

### Deep research report (user-added)
- **`plan/deep-research-report (18).md`** — Nano Banana vs GPT-Image comparison, prompt control techniques (CFG, attention editing, LoRA, ControlNet), A/B metrics, template strategies, experimental plan, technique impact table

### arthor-ai integration gap (not fixed here)
- `HeroCandidateVariation` has CTAs, nav, supportingText — **not sent** in `heroCandidatesRequestSchema`
- Default provider in arthor-ai path is effectively Google when hint omitted
- Consumer polls via `ArthorImageClient.getHeroCandidatesStatus()`

## What's next

**Immediate:** Read-only agent reads research report + current codebase, returns a **prioritized improvement plan** (no code). See kickoff prompt below.

**After plan approval (implementation backlog):**
1. Bump OpenAI default to `gpt-image-2` (+ quality tier env)
2. Evaluate Google model tier (`gemini-2.5-flash-image` vs 3.x Flash/Pro from report)
3. `hero_candidates.2` structured brief from arthor-ai
4. Wire dropped copy fields (metadata-only, not in provider prompt)
5. Inspector: show compiled prompts from run metadata pre-images
6. A/B metrics from research report (CLIPScore, brand palette drift, failure modes)
7. Commit/push uncommitted work on branch

## Open questions

- Pre-gen compile at POST adds latency (~0ms deterministic; +LLM if improver enabled) — acceptable for arthor-ai UX?
- Single batched LLM call for triad coherence vs 3 parallel vs deterministic-only?
- Google upgrade path: stay on 2.5 Flash or move to Gemini 3.1 Flash Image per report pricing/latency?
- SynthID watermark on Google outputs — acceptable for production heroes?
- Where should industry archetypes live long-term — Python registry vs JSON pack vs arthor-ai brief?

## Files the next agent should read

1. `plan/deep-research-report (18).md` — primary research input
2. `plan/HANDOFF-HERO-PROMPT-PIPELINE.md` — this file
3. `app/style/hero_prompt_compiler.py` — new deterministic compiler
4. `app/style/prompt_improver.py` — optional LLM layer
5. `app/routes/hero_candidates.py` — POST pre-gen wiring
6. `app/orchestration/hero_worker.py` — dumb worker
7. `app/providers/openai_image.py`, `app/providers/google_nano_banana.py`, `app/providers/image_model_costs.py`
8. `app/payload/hero_models.py` — variant → slot mapping
9. `scratch/hero-ab-review/REVIEW.md` — empirical A/B findings
10. `plan/adr/0010-payload-contract-v1.md`, `plan/CONTEXT.md` — domain language
11. `../arthor-ai/lib/integrations/arthor-image/hero-candidates-types.ts` — consumer contract

## Files the next agent should NOT re-read

- Full agent transcript (`2d60a3aa-54e6-4294-86fa-d845424a5cfe`)
- Entire inspector templates unless UI plan needed
- Unrelated slices/ under `slices/`

## Quirks / gotchas

- **Poll URL `google_run=` is a DB row label**, not a Google API call — interleaved `google_genai` logs are from background workers in same uvicorn process
- **Worker orphans** if uvicorn SIGKILL mid-run — stale-run reconciliation marks `failed` after ~2–5 min
- **Much work uncommitted** on `pod/w21-h-hero-candidates`; verify `git status` before assuming remote state

## Runtime (local dev)

- Uvicorn: `http://127.0.0.1:8010`
- Postgres: Docker `arthor-image-pg` port **5440**
- Merge R2 + `R2_PUBLIC_URL` from `~/arthor-ai/.env` at launch (see ledger)
