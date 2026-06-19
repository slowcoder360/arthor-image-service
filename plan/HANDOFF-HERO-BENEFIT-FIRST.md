# HANDOFF — Hero benefit-first prompts (architecture + canary)

- **From:** Canary grid grill session (Justin operator wave)
- **Date:** 2026-06-18
- **Branch:** `pod/u10-hero-taste-corpus`
- **Justin lane:** Visual QA in `/inspector/cohort-review` — **do not** enable arthor-ai default corpus until benefit-first compile is proven
- **Prior:** [`HANDOFF-HERO-CORPUS-CANARY-GRID.md`](HANDOFF-HERO-CORPUS-CANARY-GRID.md), [`HANDOFF-HERO-CORPUS-LOCKIN.md`](HANDOFF-HERO-CORPUS-LOCKIN.md)

---

## Executive summary

**Problem:** Hero provider prompts are over-layered. `scene.subject` from the U9 scene catalog wins over industry benefit text → models default to doorway consult / desk iPad / two people talking. Canary proved patches to setting/people/invariants cannot fix wrong **primary subject**.

**North star:** Hero images **sell the benefit of the service**, not generic “happy people.” No blanket rule — each trade/keyword gets a **benefit template**.

**Next work:** Implement benefit-first compiler (ADR 0013), regen failing canary slugs, Justin review, then promotion wave — **not** another layer of scene-catalog patches.

---

## Canary sessions (done)

| Session | Purpose | Human result |
|---------|---------|--------------|
| `hero-cohort-canary-20260618T144308Z` | Pass 1 — 30 slugs | 15 good / 14 bad / 1 missing (`house_cleaning`) |
| `hero-cohort-canary-20260618T170652Z` | Pass 2 — 15 bad slugs after patch wave A–D | 2 good (`pool`, `salon`) / 10 bad / 3 `missing_upload` (PT, chiro, med_spa) |

**Reports:** `scratch/hero-cohort-canary-20260618T144308Z/canary_failure_report.md`

**Pass 2 review URL:** `http://127.0.0.1:8010/inspector/cohort-review?session=hero-cohort-canary-20260618T170652Z`

**Patch wave A–D landed (compiler 3.5):** people policy, routing fixes, product-hero keywords, palette_drift QA override. **Insufficient** — scene catalog subject still dominates.

---

## Root cause (technical)

```text
HeroCandidatesRequest
  → hero_archetypes.variant_subject_primary  → Slot/seed hash ONLY
  → hero_visual_strategy.SCENE_CATALOG.subject → WINS in provider prompt
  → industry modifiers in setting/people/invariants → fight layer 2
```

File: `app/style/hero_prompt_compiler.py` line ~85: `subject=scene.subject`

**ADR 0012** intended industry = modifiers only; in practice generic archetypes (`threshold_invitation`, `desk_side_guidance`) became the hero story.

---

## Locked product decisions (grill 2026-06-18)

### People / likeness

| Context | Rule |
|---------|------|
| Provider in frame | Customer face OK; provider **back/profile** |
| WIP slots | Worker back/profile; customer face if present |
| Environment v0 | People optional; anonymous only (no identifiable staff) |
| Team refs | Default back-face; **regenerate + ref** may show likeness |
| `general_services` | **Unknown industry only** — door greet, no service imagery |

### Triad patterns by bucket

**home_services** — v0 trade-specific; v1/v2 shared:
- v0: HVAC/plumbing/electric → interior **finished comfort**; roofing/garage door → **exterior/work pride**
- v1: work in progress (trade-accurate)
- v2: post-job trust (homeowner + provider, not kitchen consult)

**outdoor_services** — v0 finished property outcome; v1 WIP **trade-accurate**; v2 second outcome angle

**healthcare** — **all 3 slots trade-specific** (PT/chiro, med spa, vet); never both in clinical attire

**dental** — 0 consult/smile, 1 family warmth, 2 smile outcome

**legal** — 0 desk counsel, 1 office threshold welcome, 2 relieved client

**office family** (CPA, insurance, property, real estate) — shared office base + trade detail on desk

**environment-first** (restaurant, cleaning, salon, pool, gym, wedding) — v0 dedicated env; v1 WIP trade-accurate; v2 second env angle

**pest** — v0 protected home exterior; **auto** — v0 clean shop bay + vehicle serviced

**concrete paving** — **dedicated template** (not home_services group); commercial vs residential drives scene (**signal TBD** — see open questions)

**Narrow `general_services`:** known industries never get door greet; dedicated keyword templates only.

---

## Target architecture

```text
resolve_industry()           → coarse label (corpus fallback, analytics)
resolve_benefit_template()   → benefit_subject + people_policy + invariants
                               (industry string + variant_index + optional commercial/residential)
compile_hero_prompt_brief()  → ONE brief; benefit_subject is line 1
scene_archetype              → metadata/triad label only (not provider subject)
```

**Deprecate for provider text:** `SCENE_CATALOG.subject` as primary; collapse duplicate modifier dicts into benefit templates.

**Keep:** safe zones, serializer invariants, `resolve_industry()`, cohort eval, inspector review, team ref regenerate path.

---

## Implementation plan (ordered)

1. **ADR** — `plan/adr/0013-hero-benefit-first-prompts.md` from this handoff
2. **Benefit template module** — keyword → `{benefit_subject, people_policy, avoid}` × variant_index 0|1|2 per decisions above; start with 30 canary slugs
3. **Compiler refactor** — `build_hero_prompt_brief()` uses `resolve_benefit_template()`; bump `COMPILER_VERSION` to 4.0
4. **Tests** — replace scene-catalog subject assertions with benefit_subject assertions in `test_hero_industry_prompts.py`
5. **Pass 3 canary** — regen all slugs that failed pass 1 or pass 2 + healthcare missing_upload
6. **Justin review** — single cohort-review session
7. **Promotion wave** (later) — good slugs → full triad → v2 corpus YAML

---

## Open questions (Justin / product)

1. **Commercial vs residential** for concrete (and future trades): infer from industry string (C), ICP keywords (A), or new ingress field (B — API change)?
2. **Dental v0 vs v2** both smile-adjacent — differentiate framing in template table?
3. **Healthcare trade-specific 1/2** — full benefit sentences per trade not yet grilled; extend table with Justin pass or sensible defaults?

---

## Do NOT

- Add more `INDUSTRY_SCENE_PEOPLE_OVERRIDES` patches on top of scene catalog subjects
- Enable arthor-ai default corpus until benefit-first pass reviewed
- Change hero API contract without Justin
- Import canary singles as 3× corpus slots

---

## Dev runtime

```bash
cd ~/arthor-image-service
git checkout pod/u10-hero-taste-corpus

# Stable server (no --reload during long gens)
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8010

# Canary subset
.venv/bin/python scripts/hero_cohort_eval.py \
  --base-url http://127.0.0.1:8010 \
  --scenario-set canary \
  --scenarios hvac roofing restaurant \
  --hero-viewport desktop

# Tests
.venv/bin/pytest tests/test_hero_industry_prompts.py tests/test_hero_visual_triad.py tests/test_hero_prompt_compiler.py -q
```

---

## Files to read (next agent)

1. This file
2. `plan/HANDOFF-HERO-CORPUS-CANARY-GRID.md`
3. `app/style/hero_prompt_compiler.py` · `hero_visual_strategy.py` · `hero_archetypes.py` · `hero_openai_prompt_serializer.py`
4. `scripts/hero_cohort_eval.py` · `scratch/hero-cohort-canary-20260618T144308Z/canary_failure_report.md`
5. Pass 2 reviews: `scratch/hero-cohort-canary-20260618T170652Z/human_review.json`

---

## Update log

- **2026-06-18** — Benefit-first grill complete; architecture handoff after canary pass 1+2 and patch wave A–D.
