# ORCHESTRATOR — arthor-image-service (Vertical prompts wave)

**You paste only the meta prompt at the bottom.**

**Status (2026-06-12):** Hero H1–H6 + industry matrix + cohort tooling on **`main` @ latest**. Justin is operator-tuning vertical prompts in inspector. **arthor-ai consumer contract frozen** until this wave closes.

---

## Slice queue

| ID | Status | HANDOFF | Done when |
|----|--------|---------|-----------|
| W21-H / H1–H6 | **DONE** | `HANDOFF-HERO-VISUAL-STRATEGY.md` | On `main` |
| **V1** | **ACTIVE** | `HANDOFF-VERTICAL-PROMPTS-AND-USER-ASSETS.md` | Justin visual pass all cohort verticals |
| V2 | OPEN | same HANDOFF § Future path | `POST /images/assets/analyze` + tests — **after V1** |
| V3 | OPEN | `HANDOFF-HERO-NEXT-AGENT.md` Path 1 | Asset-pack non-hero serializer parity — **after V1** |
| W21-H-C | BLOCKED | `HERO-CANDIDATES-CONSUMER.md` | arthor-ai repo — **after V1** |

---

## Operating rules

- Work on **`main`** (or short-lived `pod/vertical-*` branches; merge to `main` when pytest green + Justin spot-check).
- **Deterministic compile only** — no LLM for industry routing or upload classification in this wave.
- Heroes: **OpenAI only** (ADR-0012). Do not change poll/generate JSON without Justin.
- Every vertical change needs a **regression test** in `tests/test_hero_industry_prompts.py` (or extend it).
- Justin is the quality oracle — inspector thumbs-up beats pytest alone.
- Do not start arthor-ai or arthor-agent consumer work from this orchestrator.

---

## Meta prompt (paste this)

```
You are the Tier-1 orchestrator for ~/arthor-image-service — vertical hero prompt tightening wave.

Read FIRST (in order):
1. plan/ORCHESTRATOR.md
2. plan/HANDOFF-VERTICAL-PROMPTS-AND-USER-ASSETS.md
3. plan/CONTEXT.md
4. app/style/hero_archetypes.py + tests/test_hero_industry_prompts.py

Branch: main (latest). Hero pipeline already merged.

Your job:
1. Run pytest on hero test modules (listed in HANDOFF). Fix any red before edits.
2. Work vertical-by-vertical with Justin as operator:
   - dental (baseline approved — regressions only)
   - legal, home_services, healthcare, outdoor_services (active tuning)
3. For each vertical Justin flags in inspector or cohort eval:
   - Fix backdrop/job scenes in hero_archetypes.py + scene archetypes in hero_visual_strategy.py if needed
   - Adjust serializer only when compile layer insufficient
   - Add/extend regression test asserting forbidden motifs appear as Invariants
   - Re-run pytest; optional: scripts/hero_cohort_eval.py for that slug only
4. Update agent-control/dev-launch-ledger.md with cohort SHA + date when a vertical passes Justin visual review.
5. Report: per-vertical status table (pass/fail + failure_mode summary + commit SHA).

Out of scope (stop and ask Justin):
- HeroCandidatesRequest / poll API shape changes
- arthor-ai consumer wire-up
- User upload analyze API (V2)
- Asset-pack non-hero slots (V3)
- Merging unrelated repos

Model: Composer 2.5 for subagents. One vertical per subagent dispatch unless Justin says batch.

Do not merge to main without Justin if you opened a pod branch; direct commits on main OK for small prompt fixes when tests green.
```
