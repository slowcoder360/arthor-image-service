# ORCHESTRATOR — arthor-image-service

**Paste the meta prompt at the bottom of the active wave.**

---

## Wave index

| Wave | HANDOFF | Owner | Status |
|------|---------|-------|--------|
| **Completion U1–U8** | `HANDOFF-IMAGE-SERVICE-COMPLETION.md` | Orchestrator + pods | **ACTIVE** |
| Vertical prompts V1 | `HANDOFF-VERTICAL-PROMPTS-AND-USER-ASSETS.md` | **Justin only** (inspector) | Parallel — not orchestrator |
| Hero consumer | `HERO-CANDIDATES-CONSUMER.md` | arthor-ai repo | Blocked until Justin |

Shared language: `plan/CONTEXT.md`

---

## Completion slice queue (U1–U8)

| ID | Depends | Branch suggestion |
|----|---------|-------------------|
| **U1** analyze API | — | `pod/u1-asset-analyze` |
| **U2** treatment router | U1 | `pod/u2-treatment-router` |
| **U3** enhance_headshot | U1, U2 | `pod/u3-enhance-headshot` |
| **U4** pack non-hero parity | — | `pod/u4-pack-serializer` |
| **U5** user refs in pack | U1, U4 | `pod/u5-pack-refs` |
| **U6** logo placements | U1 | `pod/u6-logo-placements` |
| **U7** illustrated register | U4 | `pod/u7-illustration` |
| **U8** pack dev E2E ledger | U4 | `pod/u8-pack-e2e` |

Dispatch **one slice per subagent**. Do not fan out U3/U5 before U1+U4 land.

---

## Operating rules

- Repo: `~/arthor-image-service`, branch from `main`
- Composer 2.5 for subagents
- Tests-first: failing test → implement → green → commit
- No hero/generate poll JSON changes without Justin
- No arthor-ai / arthor-agent code from this orchestrator
- Justin does vertical prompt tuning separately — do not dispatch cohort eval unless Justin asks

---

## Meta prompt — completion wave (paste this)

```
You are the Tier-1 orchestrator for ~/arthor-image-service — product completion wave (slices U1–U8).

Read FIRST:
1. plan/ORCHESTRATOR.md
2. plan/HANDOFF-IMAGE-SERVICE-COMPLETION.md
3. plan/CONTEXT.md
4. plan/adr/0010-payload-contract-v1.md + plan/adr/0012-hero-openai-only-and-visual-strategy.md

Branch: main. Justin is separately tuning vertical hero prompts — do NOT dispatch cohort eval or hero_archetypes edits unless he asks in this chat.

Your job:
1. Walk slices U1→U8 in dependency order. Start with U1 unless Justin names a specific slice.
2. For each slice:
   - Read the slice row in HANDOFF-IMAGE-SERVICE-COMPLETION.md
   - Write failing pytest first (tests-first)
   - Implement minimal diff; match existing HMAC + inspector patterns
   - pytest green on slice scope; commit on pod branch or main per operating rules
   - Update agent-control/slice-status.md (create if missing) with slice id, SHA, pass/fail
3. Product defaults to document in U1/U2:
   - Auto-treatment when analyze confidence high
   - confirm_first_required only for low confidence / likeness / face-in-hero
   - Image-service never owns chat UX — only analyze output fields
4. After U4+U8: update agent-control/dev-launch-ledger.md with full asset-pack smoke (not hero-only).

Out of scope — stop and report:
- arthor-ai consumer wire-up
- arthor-agent SMS / preview links
- Vertical industry prompt matrix (Justin operator)
- API contract breaks without Justin

Report after each slice: one line summary + SHA + test count. After U1 lands, pause for Justin only if analyze library choice (face detection) needs approval.

Model: Composer 2.5 for subagents. One slice per subagent dispatch.
```
