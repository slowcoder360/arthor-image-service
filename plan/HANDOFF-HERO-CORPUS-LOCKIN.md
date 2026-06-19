# HANDOFF — Hero corpus lock-in (Justin operator wave)

- **From:** Hero prompt tuning + cohort eval + U9/U10 taste corpus sessions
- **Date:** 2026-06-17
- **Branch:** `pod/u10-hero-taste-corpus` @ `df182c6` (includes U9 visual triad + U10 corpus mode)
- **Justin lane:** Visual QA + corpus approval — **do not** enable arthor-ai default corpus until 6/6 labels locked
- **Prior chats:** [Cohort/prompt tuning](dddbc48d-03cc-4cdd-a7fb-89f880005e5d) · [U9/U10 corpus pod](711b96fa-3792-4614-8973-a26e9ebdb8b5)

---

## What we're doing

Lock **six industry hero taste corpora** (3 distinct images each) so builder `generation_mode: "corpus"` serves Justin-approved plates with zero OpenAI cost. Composition, safe-zone, and realism are **good enough to freeze** (compiler **3.4**, `INDUSTRY_VISUAL_TRIAD`). Remaining work is **targeted prompt patches**, **selective live regens**, **human review**, and **YAML import** — not blanket 15-image cohort reruns.

**Seo-service** owns rich planning (`asset_pack_plan` → PayloadV1 at build time). **Image-service** owns industry archetypes, visual triad, serializer, corpus YAML. Do not duplicate industry matrix in seo-service.

---

## Architecture (locked)

| Layer | Owner | Responsibility |
|-------|-------|----------------|
| Industry backdrop + invariants | image-service | `hero_archetypes.py`, `hero_openai_prompt_serializer.py` |
| Three distinct feels per triad | image-service U9 | `INDUSTRY_VISUAL_TRIAD` in `hero_visual_strategy.py` |
| Builder hero default | image-service U10 | `generation_mode: "corpus"` → `data/hero_taste_corpus/v1/*.yaml` |
| Live gen escape hatch | image-service | `generation_mode: "live"` or `corpus_fallback: "live"` |
| Pack slot planning | seo-service | `asset_pack_plan` — **not** read by image-service directly |
| Headlines in images | **never** | copy_metrics / overlay only (ADR + consumer docs) |

---

## What's done

- **U1–U8** completion wave on `pod/u-completion-wave` (analyze, pack serializer, etc.)
- **U9** index-driven visual triad — compiler **3.4**
- **U10** corpus mode, import script, `/inspector/taste-corpus`
- **v3.3 industry prompt hardening** — legal/home/healthcare/outdoor archetypes + tests
- **Cohort eval tooling** — `scripts/hero_cohort_eval.py` (`--scenario-set triad` | `spot-check`), `/inspector/cohort-review`
- **Human reviews saved:**
  - `scratch/hero-cohort-eval-20260612T173047Z/human_review.json` (pre-v3.3 baseline)
  - `scratch/hero-cohort-eval-20260613T180628Z/human_review.json` (v3.3 triad)
  - `scratch/hero-cohort-spot-20260615T183212Z/` — 18 images generated; **review optional / may be incomplete**

---

## Corpus truth table (YAML vs Justin approval)

Current YAML under `data/hero_taste_corpus/v1/` is **dev seed** — U10 pod backfilled from mixed old runs. **Only legal is corpus-ready from human review.**

| Label | YAML status | Source run (today) | Justin verdict | Action |
|-------|-------------|-------------------|----------------|--------|
| **legal** | 3/3 | v3.3 `fa4dd7fa…` | **3/3 good** | **Lock** — verify taste-corpus page, no regen |
| **outdoor_services** | 3/3 | v3.3 landscaping `854ca864…` | **2/3 good** (offer = yard-only) | Regen **variant 2** only; keep 0+1 |
| **home_services** | 3/3 | Old HVAC rerun `43b236cc…` | v3.3 **offer perfect** on `db68af28…`; story bad | Import offer slot; regen search + story |
| **healthcare** | 3/3 | Spot chiro `32752bb8…` (**unreviewed**) | v3.3 PT **1/3 good** (offer); attire issues | **Attire patch** → full live triad → review |
| **dental** | 3/3 | Jun 12 `75308b54…` | 3/3 Jun 12 but **female-only** concern | Regen triad w/ diversity cues OR v3.3 `21ffc2bc…` after review |
| **general_services** | 3/3 | Jun 12 `1e775877…` | **0/3 bad** Jun 12 | **Full regen** (pest control spot scenario) |

---

## Remaining prompt patches (minimal — then freeze)

Apply **only** before regen for affected labels:

1. **Healthcare** — enforce clinical attire (scrubs, white coat); block business-casual / gym in serializer + `avoid_extra`
2. **Home services story** — on-site technician; exclude patio/table hybrid (`home_services` archetype)
3. **Dental** — people-policy diversity in serializer or archetype trust/experience scenes (gender mix)
4. **General_services** — keep separate from `outdoor_services`; use pest/cleaning match keys
5. **Auto QA** — do not use `palette_drift` as human-quality gate (landscaping false-failed 2/3 good images)

After patches: bump `COMPILER_VERSION` only if prompt hash semantics change; update `test_hero_industry_prompts.py`.

---

## Operator loop (one industry at a time)

```bash
cd ~/arthor-image-service
git checkout pod/u10-hero-taste-corpus

# Dev server (reload recommended)
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload

# 1) Inspect compiled prompts (hero-ab) — three variant indices = three scene_archetypes
open http://127.0.0.1:8010/inspector/hero-ab

# 2) Live generate ONE industry triad
.venv/bin/python scripts/hero_cohort_eval.py \
  --base-url http://127.0.0.1:8010 \
  --scenarios <slug> \
  --hero-viewport desktop
# Or POST with "generation_mode": "live" in payload

# 3) Human review
open http://127.0.0.1:8010/inspector/cohort-review?session=<session_dir_name>

# 4) Import good slots to corpus YAML
.venv/bin/python scripts/import_cohort_to_corpus.py \
  --cohort-csv scratch/<session>/cohort_results.csv \
  --reviews scratch/<session>/human_review.json \
  --industry-label <label>

# 5) Verify corpus grid
open http://127.0.0.1:8010/inspector/taste-corpus

# 6) pytest
.venv/bin/pytest tests/test_hero_industry_prompts.py tests/test_hero_visual_triad.py \
  tests/test_hero_taste_corpus.py tests/test_import_cohort_to_corpus.py -q
```

**Recommended industry order:** legal (verify) → dental → home_services → healthcare → outdoor_services (slot 2) → general_services.

---

## Done when

- [ ] All six labels have **3/3 Justin-approved** images in `data/hero_taste_corpus/v1/<label>.yaml`
- [ ] `/inspector/taste-corpus` shows **distinct** images per row (no general_services fallback in inspector)
- [ ] Each triad has **three visually distinct feels** (triad archetypes, not three copies of same scene)
- [ ] `pytest` hero slice green
- [ ] `plan/HANDOFF-HERO-TASTE-CORPUS.md` corpus table updated
- [ ] Justin signs off → arthor-ai may default `generation_mode: "corpus"`

---

## Do NOT

- Re-run full 5×3 triad matrix for composition tuning (solved)
- Change hero poll/generate JSON without Justin
- Put industry backdrop logic in seo-service
- Ship corpus as default with current YAML seed without per-industry visual pass
- Dispatch parallel live gens across all six industries without Justin review between imports

---

## Files to read

1. `plan/HANDOFF-VERTICAL-PROMPTS-AND-USER-ASSETS.md` — prompt layer map
2. `plan/HANDOFF-HERO-TASTE-CORPUS.md` — U9/U10 machinery
3. `plan/HERO-CANDIDATES-CONSUMER.md` — corpus vs live vs seo boundary
4. `app/style/hero_archetypes.py` · `hero_visual_strategy.py` · `hero_openai_prompt_serializer.py`
5. `scripts/import_cohort_to_corpus.py` · `scripts/hero_cohort_eval.py`
6. `scratch/hero-cohort-eval-20260613T180628Z/human_review.json` — v3.3 approvals

---

## Gotchas

- Stale uvicorn without `--reload` → new inspector routes 404; taste-corpus needs login (401 not 404)
- U10 pod initially used `cdn.example` placeholders + landscaping fallback for missing industries
- `import_cohort_to_corpus.py` keys reviews as `{run_id}:{variant_index}` — export or point `--reviews` at session `human_review.json`
- API always generates 3 variants per request; cohort CSV can record all 3 (default)

---

## Update log

- **2026-06-17** — Initial lock-in handoff after v3.3 cohort + spot-check + U10 seed audit
