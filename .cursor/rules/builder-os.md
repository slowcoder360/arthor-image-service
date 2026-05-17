# builder-os agent rules

Foundation rules for any project running the builder-os orchestration loop. Synced into a target project by the [`foundation-sync`](../../skills/foundation-sync/SKILL.md) skill.

These rules apply to **every** agent operating in the project — the high-level orchestrator and every Composer 2 subagent.

---

## Packet rules

- **Read-only**: agents must NEVER modify any file under `packet/`. Packets are owned by the human. Capture answers to ambiguity in `scratch/intake-notes.md` instead.
- **Validate before use**: every run starts with a packet schema check. Fail fast on invalid packets.
- **Don't silently expand scope**: if a slice needs information not in the packet, surface a question. Don't invent.

## Plan rules

- **Plan before slicing**: `plan/plan.md`, `plan/CONTEXT.md`, and `plan/adr/` exist before any slice is written.
- **One ADR per non-obvious decision.** Append-only. To change a decision, write a new ADR that supersedes the old one.
- **Shared language wins.** Use the terms in `plan/CONTEXT.md` consistently across slice specs, commits, and PR descriptions.

## Slice rules

- **Vertical, not horizontal.** A slice delivers a user-visible behavior, not a layer.
- **Explicit scope.** Every slice spec lists `paths_in_scope` and `paths_out_of_scope`.
- **No silent scope expansion.** Touching a path outside scope requires updating the spec first, with a `## Scope changes` note.

## Test rules (strict TDD ownership)

- **High-level agent writes tests.** Composer 2 subagents only write implementation.
- **Test files are out of scope for subagents.** A subagent that modifies a test file fails review automatically.
- **Tests must run red before any subagent dispatches.** "Tests not running" is not "tests passing".
- **One reason to fail per test.** Test names read like sentences.

## Subagent rules

- **Worktree by default.** Use `best-of-n-runner` for any non-trivial slice. `generalPurpose` only for tiny edits.
- **Composer 2 for implementation.** `composer-2-fast` model for builders unless explicitly overridden.
- **Completion signal required.** A subagent that finishes without `<builder-os>COMPLETE</builder-os>` (or its configured equivalent) is not done.
- **No narration.** Subagents should read, edit, run, report. No prose explaining intent.
- **Branch naming**: per the dispatch prompt's `target_branch`. Defaults to `builder/<slice-id>` only if no target is given. Projects with an existing PR-branch convention (e.g. `phase-X.Y-name`, `feat/<slug>`) pass their own value via [`dispatch-from-issue`](../../skills/dispatch-from-issue/SKILL.md) so the orchestrator never has to rename branches post-hoc.

## Run output rules

- **Every dispatch writes a run-result.** `scratch/run-results/<slice-id>.json` matching the schema at `~/builder-os/schemas/run-result.schema.json`.
- **Every review appends, doesn't overwrite.** A second review pass adds an entry; it doesn't clobber the first.
- **`scratch/last-run.md`** holds the latest human-readable summary.

## Build & quality rules

- **Build must pass.** No broken builds merged.
- **No type errors.** Strict mode where the language supports it.
- **No new dependencies without an ADR.** A new dep is a non-obvious decision.
- **Pin versions.** Floating versions break determinism.

## Security rules

- **No secrets in repo.** Use environment variables. Never commit `.env` files except `.env.example`.
- **No API keys in PACKET.md.** Packets are config, not credentials.
- **No live credentials in tests.** Use fixtures or mocks.

## MCP rules (when reviewing)

- **Prefer MCPs over reading diffs.** Use `code-review-graph` for structural review, `log-reader-mcp` for runtime evidence, `chrome-devtools` (or `cursor-ide-browser`) for UI verification.
- **Read MCP tool descriptors before invoking.** Schemas live under `~/.cursor/projects/empty-window/mcps/<server>/tools/`.
- **Save MCP outputs to scratch when material.** Screenshots, profile reports, structural reports go in `scratch/review-evidence/`.

## Token discipline rules

- **Research happens in `explore` subagents.** The orchestrator does not grep the codebase directly.
- **Implementation happens in `composer-2-fast` subagents.** The orchestrator does not write feature code directly.
- **Run [`context-primer`](../../skills/context-primer/SKILL.md) at 50–60% token usage.** Don't wait for the wall.

## Communication rules

- **No em dashes in user-visible copy** (this is a project-author preference inherited from agent-packet conventions; remove if not relevant to your project).
- **No filler in agent output.** "Sure thing!", "Great question!", "Let me…" are wasted tokens. Be direct.
- **Cite paths with `file:line` format** when pointing at code.
