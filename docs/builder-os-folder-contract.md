# builder-os repo folder contract

Standard layout for a project running the builder-os loop. Created by [`setup-builder-os`](../../skills/setup-builder-os/SKILL.md) and synced by [`foundation-sync`](../../skills/foundation-sync/SKILL.md).

## Required structure

```
project-root/
├── packet/                   # INPUT — human-owned, agent read-only
│   ├── PACKET.md
│   ├── refs/                 # supporting docs, screenshots, transcripts
│   ├── data/                 # CSVs, JSON, sample inputs
│   └── schemas/              # API contracts, type defs
├── plan/                     # PLANNING — orchestrator-owned
│   ├── plan.md
│   ├── CONTEXT.md
│   └── adr/
│       ├── 0001-<name>.md
│       └── 0002-<name>.md
├── slices/                   # WORK BREAKDOWN — orchestrator-owned
│   ├── README.md             # index + dependency Mermaid
│   └── <slice-id>/
│       ├── SPEC.md           # the brief; subagents read but never modify
│       └── tests/            # failing tests; subagents read but never modify
├── scratch/                  # WORKING NOTES — orchestrator + subagent write
│   ├── intake-notes.md
│   ├── research/             # explore-subagent dumps
│   ├── run-results/
│   │   └── <slice-id>.json   # one per dispatch, schema in ~/builder-os/schemas/
│   ├── review-evidence/
│   │   └── <slice-id>/       # screenshots, profile dumps, MCP findings
│   ├── handoff/
│   │   └── primer-<ts>.md
│   └── last-run.md           # latest human-readable summary
├── src/                      # PROJECT CODE — subagents write within slice scope
└── .cursor/
    ├── builder-os.json       # project config (subagent defaults, MCP list, signals)
    └── rules/                # synced from ~/builder-os/foundation/cursor/rules.md
```

## Permissions

| Path | Orchestrator | Subagent |
|---|---|---|
| `packet/` | read | read |
| `plan/` | read/write | read |
| `slices/<id>/SPEC.md` | read/write | read |
| `slices/<id>/tests/` | read/write | read |
| `scratch/` | read/write | read/write (their slice's subdir) |
| `src/` | read | read/write (within slice scope) |
| `.cursor/` | read | read |

## Hard rules (mirrors `foundation/cursor/rules.md`)

- Never modify files under `packet/`.
- Never modify `slices/<id>/SPEC.md` or `slices/<id>/tests/` from a subagent.
- Subagent edits must stay within their slice's `paths_in_scope`.
- Every dispatch writes a `scratch/run-results/<slice-id>.json` and updates `scratch/last-run.md`.

## What lives outside `scratch/`

- `plan/` is durable. ADRs are append-only.
- `slices/` is durable. The history of slice specs is the history of the build.
- `scratch/` is throwaway. Add to `.gitignore` if you don't want it in version control. (`setup-builder-os` does this by default.)
