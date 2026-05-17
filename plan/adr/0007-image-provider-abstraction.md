# ADR 0007: Image provider abstraction

- Status: proposed
- Date: 2026-05-17

## Context

Research subagent #11 documented that no image-provider abstraction exists anywhere in the arthor ecosystem. The closest analogs are arthor-ai's `AiAdapter` TS interface (`lib/ai/adapter.ts:16-25`) and arthor-agent's `EmailProviderAdapter` Python Protocol (`communications/providers/email/base.py:8-19`). arthor-agent's harness has a `record_llm` / `record_tool` cost-tracking flush pattern in `agent_runtime/harness.py`.

The packet sketches an `ImageProvider` Protocol with `generate_single` and `generate_pack_consistent`. Two concrete providers in v1: OpenAI image (likely `gpt-image-1` or its successor) and Google Gemini 2.5 Flash Image ("nano-banana").

## Options considered

- **A. `typing.Protocol` with `@runtime_checkable`** — PEP 544 structural typing; matches arthor-agent's `EmailProviderAdapter` style; no ABC inheritance required.
- **B. `abc.ABC` with `@abstractmethod`** — matches arthor-agent's `ProviderAdapter` style; enforces method presence at subclass declaration.
- **C. Pydantic-modelled provider config + factory function** — easier config-driven swapping but loses static method-signature checking.

## Decision

**Option A — `typing.Protocol` with `@runtime_checkable`**, matching arthor-agent's `EmailProviderAdapter`.

Specifics:

```python
# app/providers/protocol.py
from typing import Protocol, runtime_checkable
from dataclasses import dataclass

from app.style.profile import StyleProfile
from app.payload.models import SlotPrompt

@dataclass
class ProviderResult:
    image_bytes: bytes
    width: int
    height: int
    seed: int | None
    provider: str
    model_version: str
    cost_cents: int
    latency_ms: int
    external_id: str | None
    response_shape: dict  # trimmed (no body) for tool_calls.result
    determinism_level: str  # "strict" | "best-effort" | "none"

@runtime_checkable
class ImageProvider(Protocol):
    name: str  # "openai_image" | "google_nano_banana"
    supports_pack_consistent: bool
    supports_reference_image: bool

    async def generate_single(
        self,
        *,
        prompt: str,
        dimensions: tuple[int, int],
        seed: int | None,
        style_profile: StyleProfile,
        reference_images: list[bytes] | None = None,
    ) -> ProviderResult: ...

    async def generate_pack_consistent(
        self,
        *,
        prompts: list[SlotPrompt],
        style_profile: StyleProfile,
        seed: int | None,
    ) -> list[ProviderResult]: ...
```

Concrete implementations:

- `app/providers/openai_image.py` — `OpenAIImageProvider`. `supports_pack_consistent = False` (falls back to N parallel `generate_single` with shared style profile + reference conditioning). `supports_reference_image = True`. `determinism_level = "best-effort"` (OpenAI image API does not expose a user seed in current public docs).
- `app/providers/google_nano_banana.py` — `GoogleNanoBananaProvider`. `supports_pack_consistent = True` (Gemini Flash Image supports multi-image native consistency calls). `supports_reference_image = True`. `determinism_level = "strict"` if seed is honored at implementation time; downgrade to `best-effort` if not.

**Pack-consistent fallback strategy** for providers where `supports_pack_consistent = False`: generate the hero first via `generate_single`, then call `generate_single` for each non-hero slot with `reference_images=[hero_bytes]` and the same `StyleProfile`. The orchestrator (`app/asset_pack/runner.py`) handles this branch.

**Retry policy** (per intake decision E): each failed `generate_single` call is auto-retried once with a new seed and the same prompt. If the retry also fails, the slot's `external_media_assets` row gets `status='failed'` and the pack callback returns `status=partial`.

**Provider registry** in `app/providers/__init__.py` is a simple dict `{name: provider_class}`. Routing per slot is deterministic per ADR-0009 (rules per `slot_kind` with payload `provider_hint` override).

**Cost-tracking pattern** (mirror arthor-agent's harness): each provider call is wrapped by `app/persistence/tool_calls.py:record_provider_call(...)` which:
1. Inserts a `tool_calls` row with `status='running'` (we add this status via ADR-0004's CHECK update — actually, arthor-agent's CHECK is `ok|error|skipped` only; we'd need to relax it; better: insert the row only after the call completes).
2. Awaits the provider's `generate_single` or `generate_pack_consistent`.
3. Inserts the `tool_calls` row with the result fields (`cost_cents`, `latency_ms`, `provider`, `model_version`, trimmed `args`, trimmed `result`, `status='ok'` or `error`).

## Consequences

What gets easier:
- Adding a third provider (e.g. Black Forest Labs FLUX) is one new file in `app/providers/`.
- Mocking for tests is trivial — implement the Protocol in `tests/_fixtures/mock_provider.py`.

What gets harder:
- Per-provider quirks (model version pinning, seed support, response shape) leak into the orchestrator. Mitigation: keep all quirks behind the `ProviderResult` dataclass; the orchestrator only consumes the abstraction.
- If a future provider has a fundamentally different async streaming shape, the Protocol breaks. Acceptable for v1; revisit if it bites.
