# arthor-image-service

**New here?** Read [`docs/agents/domain.md`](docs/agents/domain.md), then [`plan/CONTEXT.md`](plan/CONTEXT.md), then [`plan/adr/`](plan/adr/).

This repository is a FastAPI service that generates and manages image assets for Arthor workflows: it accepts validated payload contracts, coordinates providers (OpenAI, Gemini, etc.), writes durable run records and storage keys, and exposes an operator-facing inspector. Module map: `app/payload/` for request schemas and idempotency; `app/runs/` for agent run and tool-call persistence; `app/style/` for style profiles and prompt building; `app/storage/` for R2 and cold-storage helpers; `app/providers/` for image backends; `app/routes/` for HTTP route modules; `app/orchestration/` for workers and pack pipelines; `app/inspector/` for Jinja/HTMX UI; `app/jobs/` for scheduled tasks; `db/migrations/` for raw SQL migrations.

When editing this codebase: only change what you need to change do not completely rewrite files. always ask permission before making changes that i did not ask for directly.
