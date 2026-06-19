# HANDOFF — Hero corpus canary grid (v2 discovery wave)

- **From:** Hero corpus lock-in sessions (Justin operator wave) → strategy pivot
- **Date:** 2026-06-18
- **Branch:** `pod/u10-hero-taste-corpus` (U9 triad + U10 corpus mode, compiler **3.4**)
- **Justin lane:** Visual QA in `/inspector/cohort-review` — **do not** enable arthor-ai default `corpus` until canary + promotion path is proven
- **Prior handoff:** [`HANDOFF-HERO-CORPUS-LOCKIN.md`](HANDOFF-HERO-CORPUS-LOCKIN.md) (v1 coarse wave — superseded for coverage strategy, not for machinery)

---

## What we're doing

**Stop treating six coarse buckets as sufficient coverage.** Run a **canary grid**: ~30–50 edge scenarios × **1 image each** to find prompt/routing/model weaknesses before locking corpus plates. **Promote** passers to full 3-plate triads into **corpus v2** (per-slug YAML + better `resolve_taste_corpus` matching). v1 coarse YAML remains **fallback only**, not the product mapping.

**Seo-service** still owns `asset_pack_plan` at build time. **Image-service** owns archetypes, canary matrix, corpus import, inspector review. Headlines never in provider prompts.

---

## Architecture (updated)

| Layer | v1 (today) | v2 (target) |
|-------|------------|-------------|
| Discovery | Full triad per coarse label | **Canary grid** — 1 image / scenario slug |
| Storage | `data/hero_taste_corpus/v1/{label}.yaml` (6 files) | `v2/{slug}.yaml` — one triad per slug after promotion |
| Resolution | `resolve_industry()` → 6 labels → 1 file | Longest `match_keys` match across slug files → coarse fallback → `general_services` → live |
| Builder contract | 3 URLs on poll | **Unchanged** — promotion still 3 distinct feels (U9 triad) |

```text
Edge slug → 1 canary gen → human review
  → bad: tag issue → patch archetype/serializer → re-canary
  → good: full triad gen → 3/3 review → import v2/{slug}.yaml
```

---

## v1 corpus status (as of 2026-06-18)

**Do not ship arthor-ai default corpus on this alone** — two slots lack Justin approval.

| Label | Locked | Gap |
|-------|--------|-----|
| legal | **3/3** | — |
| dental | **3/3** | — |
| healthcare | **3/3** | Justin noted female-only providers; optional diversity regen |
| outdoor_services | **3/3** | Landscaping-biased; headlines are preview-only |
| home_services | **2/3** | Slot 1 story — `missing_upload` in batch; placeholder in YAML |
| general_services | **2/3** | Slot 1 story — doorway roles swapped (human_review bad) |

YAML: `data/hero_taste_corpus/v1/*.yaml`  
Inspector: `http://127.0.0.1:8010/inspector/taste-corpus`

**Key reviews:** `scratch/hero-cohort-eval-20260617T202916Z/human_review.json` (batch)

---

## Prompt patches already landed (freeze unless canary fails)

- Dental / healthcare people diversity & clinical attire
- Home services doorway orientation + patio/table story exclusions
- `scripts/hero_cohort_eval.py` sends `generation_mode: "live"`
- Outdoor + general_services cohort scenarios split (`outdoor_services` vs `pest control`)
- Ignore `palette_drift` for human QA (Justin override on landscaping)

---

## Canary grid — orchestrator deliverables

### 1. Tooling

Extend `scripts/hero_cohort_eval.py`:

- `--scenario-set canary` (documented in lock-in handoff but **not implemented**)
- `CANARY_SCENARIOS[]` — see matrix below
- **One image per slug:** single-variant payload (variant 0 / search / trust) unless slug notes otherwise
- Output: `scratch/hero-cohort-canary-{ts}/` with `cohort_results.csv`, `cohort_summary.md`, failure aggregation by slug + issue tag
- Review URL: `/inspector/cohort-review?session=<dir>`

### 2. Canary matrix (first 30 slugs)

Each row: `slug`, `business.industry`, `expected_label` (assert `resolve_industry()`), optional `site_name`.

| slug | industry string | expected_label |
|------|-----------------|----------------|
| dental | dental | dental |
| orthodontics | orthodontist | dental |
| personal_injury_law | personal injury law | legal |
| family_law | family law attorney | legal |
| hvac | hvac repair | home_services |
| plumbing | plumbing service | home_services |
| roofing | roofing contractor | home_services |
| electric | electrician | home_services |
| garage_door | garage door repair | home_services |
| pest_control | pest control | general_services |
| house_cleaning | house cleaning service | general_services |
| landscaping | landscaping | outdoor_services |
| arborist | arborist tree care | outdoor_services |
| tree_removal | tree removal service | outdoor_services |
| concrete_paving | concrete paving contractor | general_services |
| pool_service | pool cleaning service | general_services |
| fencing | fence installation | outdoor_services |
| physical_therapy | physical therapy clinic | healthcare |
| chiro | chiropractor | healthcare |
| veterinary | veterinary clinic | healthcare |
| med_spa | medical spa | healthcare |
| auto_repair | auto repair shop | general_services |
| salon | hair salon | general_services |
| restaurant | restaurant | general_services |
| property_management | property management | general_services |
| insurance_agency | insurance agency | general_services |
| cpa | cpa accounting firm | general_services |
| gym | fitness gym | general_services |
| real_estate | real estate agent | general_services |
| wedding_venue | wedding venue | general_services |

**Pass 2 (later):** re-canary weakest archetype per bucket (story slot for home_services, etc.).

### 3. After Justin reviews

- Aggregate `human_review.json` → `canary_failure_report.md` (counts by issue tag + slug)
- Patch prompts only where tags cluster
- **Promote** good slugs → full triad gen → import (new script or extend `import_cohort_to_corpus.py` for v2 slug files)
- **Do not** import canary singles into builder corpus as 3× duplicate

### 4. v2 resolver (after promotion wave)

- `resolve_taste_corpus(industry)` scans `v2/*.yaml` `match_keys`, longest win
- Fallback: v1 coarse label → `general_services` → `corpus_fallback: live`
- `corpus_version: "2.0"` on ingress when ready

---

## Operator runtime

```bash
cd ~/arthor-image-service
git checkout pod/u10-hero-taste-corpus

# Dev server
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
# Merge R2 from ~/arthor-ai/.env if needed

# Canary batch (after orchestrator implements --scenario-set canary)
.venv/bin/python scripts/hero_cohort_eval.py \
  --base-url http://127.0.0.1:8010 \
  --scenario-set canary \
  --hero-viewport desktop

# Review
open http://127.0.0.1:8010/inspector/cohort-review?session=<session_dir>

# Tests
.venv/bin/pytest tests/test_hero_industry_prompts.py tests/test_hero_visual_triad.py -q
```

---

## Do NOT

- Enable arthor-ai default `generation_mode: "corpus"` until canary + promotion path signed off
- Duplicate one canary image across 3 builder slots
- Change hero poll/generate JSON without Justin
- Put industry logic in seo-service
- Use `palette_drift` as human-quality gate
- Re-run full 6×3 coarse matrix for composition tuning (solved)

---

## Done when (canary wave)

- [ ] `CANARY_SCENARIOS` + `--scenario-set canary` implemented and tested
- [ ] ~30 canary images generated in one session
- [ ] Justin reviewed all rows in cohort-review
- [ ] `canary_failure_report.md` published from reviews
- [ ] Prompt patches applied for clustered failures (minimal diffs)
- [ ] Good slugs promoted to full triad (separate wave)

## Done when (v2 corpus — later)

- [ ] Slug-level YAML under `data/hero_taste_corpus/v2/`
- [ ] Resolver prefers slug match over coarse label
- [ ] Justin signs off → arthor-ai may default `corpus_version: "2.0"`

---

## Files to read (orchestrator)

1. This file
2. [`HANDOFF-HERO-CORPUS-LOCKIN.md`](HANDOFF-HERO-CORPUS-LOCKIN.md) — v1 machinery + operator loop
3. [`HERO-CANDIDATES-CONSUMER.md`](HERO-CANDIDATES-CONSUMER.md) — corpus vs live boundary
4. `scripts/hero_cohort_eval.py` · `app/style/hero_taste_corpus.py` · `app/style/hero_archetypes.py`
5. `scratch/hero-cohort-eval-20260617T202916Z/` — latest batch reviews

---

## Gotchas

- Cohort eval without `generation_mode: live` hits corpus DB constraint (`provider_chk`)
- uvicorn `--reload` during long gens can orphan runs — avoid editing scripts mid-batch
- `import_cohort_to_corpus.py` expects CSV reviews + exactly 3 variants per YAML — canary singles are **not** import-ready
- Home services story slot repeatedly `missing_upload` — investigate worker, not just prompts
- Cohort preview headlines (e.g. "Landscaping…") are inspector overlay only — not burned into images

---

## Update log

- **2026-06-18** — Pivot from v1 coarse lock-in to canary grid + v2 slug corpus; v1 status table updated from Justin batch reviews.
