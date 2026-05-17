---
id: s04-payload-contract
title: PayloadV1 pydantic models, strict validation, idempotency, image_request_payloads writer, JSON Schema export
depends_on: [s02-db-pool-and-migrations-001, s03-auth]
parallel_safe: true
estimated_loc: 700
---

# s04-payload-contract — Rich payload contract v1 (foundational slice)

## Summary

The highest-leverage slice in the build. Materializes the full ADR-0010 payload contract as pydantic v2 models (`PayloadV1` + 13 sub-models), strict validators that surface a `payload_completeness_score`, an idempotency check against `image_request_payloads`, the writer that persists the payload, and a build-time generator that exports `docs/payload-schema.v1.json` from the pydantic models. Every downstream slice (resolver, providers, endpoints) consumes these models — getting the contract wrong here cascades. No routes mounted; the contract is just primitives.

## Acceptance criteria

- AC-1: `app/payload/models.py` defines `PayloadV1` and the 13 sub-models exactly per ADR-0010 (`Business`, `Location`, `BrandVoice`, `BrandVisual`, `Palette`, `Typography`, `CustomerReferenceAsset`, `StyleProfileHint`, `Pack`, `ReferencePolicy`, `Slot`, `SlotRoute`, `SlotSection`, `SlotCopyContext`, `SlotSubject`, `SlotPeoplePolicy`, `SlotCamera`, `SlotLightingMood`, `SlotLayout`, `SlotSafeArea`) — count by your own grouping; the model graph matches ADR-0010 JSON shape exactly. `PayloadV1.payload_version: Literal["1.0"]`. `PayloadV1.idempotency_key: str = Field(min_length=8)`.
- AC-2: All hex color fields are validated with a regex (`^#[0-9A-Fa-f]{6}$`). All URL fields use `pydantic.HttpUrl`. All UUID fields use `pydantic.UUID4`. `country` is `Literal[ISO 3166-1 alpha-2]` — accept a curated list (US, CA, GB, etc.) OR fall back to a length-2 uppercase regex for v1; document the choice in code.
- AC-3: `app/payload/validator.py` exports `validate_payload(raw: bytes | dict) -> tuple[PayloadV1, ValidationReport]`. `ValidationReport` has `errors: list[ValidationError]`, `warnings: list[str]`, `completeness_score: float` (0.0-1.0 per ADR-0010 §"Minimum-viable payload"). The MVP set scores 0.4 (just the required fields); 1.0 means every optional field is populated. Returns errors structured, never raises on validation issues (raises only on malformed JSON when input is bytes).
- AC-4: `app/payload/validator.py` rejects `payload_version` other than `"1.0"` with a clear structured error referencing the v1.x versioning policy. Accepts `1.0` only in v1; `1.x` would warn-and-accept once defined (out of scope here).
- AC-5: `app/payload/idempotency.py` exports `async def lookup_idempotency_key(pool, idempotency_key: str) -> uuid.UUID | None` that queries `image_request_payloads WHERE idempotency_key = $1` and returns the associated `agent_run_id` or None. Constant-time on the DB side via the unique index.
- AC-6: `app/payload/repository.py` exports `async def insert_payload_record(pool, *, agent_run_id, payload: PayloadV1, payload_version: str, idempotency_key: str, source: str = "arthor-ai") -> uuid.UUID`. Writes `image_request_payloads` row with `payload_hash = sha256(canonical_json(payload))` using `json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))`. Raises a typed `IdempotencyConflict` if the unique constraint trips.
- AC-7: `app/payload/schema_export.py` exports `def export_json_schema(out_path: Path) -> None` that calls `PayloadV1.model_json_schema()` and writes formatted JSON to `out_path`. Run during s04 implementation to populate `docs/payload-schema.v1.json` — the generated file is committed.
- AC-8: `docs/payload-schema.v1.json` is the JSON Schema 2020-12 representation of `PayloadV1`, regeneratable via `python -m app.payload.schema_export docs/payload-schema.v1.json`.
- AC-9: `PayloadV1.payload_completeness_score()` (instance method) returns the same score as `ValidationReport.completeness_score`. Lets callers compute the score after the fact.

## Paths in scope

- `app/payload/__init__.py`
- `app/payload/models.py`
- `app/payload/validator.py`
- `app/payload/idempotency.py`
- `app/payload/repository.py`
- `app/payload/schema_export.py`
- `docs/payload-schema.v1.json` (generated, committed)

## Paths out of scope (do not touch)

- `app/main.py` — no routes mounted here.
- `app/auth/**` (s03), `db/**` (s02), `app/runs/**` (s05), `app/style/**` (s06), `app/storage/**` (s07), `app/providers/**` (s08/s09), `app/routes/**` (s10/s11/s12), `app/inspector/**` (s13)
- `slices/**`, `plan/**`, `packet/**`, `scratch/**`

## Failing tests the subagent must turn green

- `slices/s04-payload-contract/tests/test_payload_v1_full.py` — round-trip parse + dump of a maximal example payload (every field set); asserts model output equals input modulo type coercion.
- `slices/s04-payload-contract/tests/test_payload_v1_mvp.py` — parse + dump of the MVP-only payload (ADR-0010 §"Minimum-viable payload"); asserts completeness_score in `[0.35, 0.45]`.
- `slices/s04-payload-contract/tests/test_hex_color_validation.py` — table-driven: `#0A4B6F` ok; `#0a4b6f` ok; `0A4B6F` rejected; `#GGG` rejected.
- `slices/s04-payload-contract/tests/test_payload_version_gate.py` — `"1.0"` accepted; `"2.0"` rejected with documented error; `"1.1"` (unknown 1.x) accepted with a warning (per versioning policy).
- `slices/s04-payload-contract/tests/test_validator_report_shape.py` — `validate_payload` returns the documented `ValidationReport`; never raises on validation issues; raises only on bytes-input that aren't valid JSON.
- `slices/s04-payload-contract/tests/test_idempotency_lookup.py` — `requires_db` — insert a row, lookup by key returns the run_id; lookup of unknown key returns None.
- `slices/s04-payload-contract/tests/test_insert_payload_record.py` — `requires_db` — insert returns the row id; the row's `payload_hash` matches sha256 of canonical JSON; second insert with same `idempotency_key` raises `IdempotencyConflict`.
- `slices/s04-payload-contract/tests/test_canonical_json_hash.py` — asserts `payload_hash` is stable across two identical payloads passed in different key orders.
- `slices/s04-payload-contract/tests/test_schema_export.py` — runs `export_json_schema(tmp_path / "schema.json")` and asserts the file parses as JSON Schema 2020-12; `properties.payload_version.const == "1.0"`.
- `slices/s04-payload-contract/tests/test_completeness_score.py` — empty-MVP vs maximal payload scores differ by at least 0.5.

## Hints

- ADR anchor: [plan/adr/0010-payload-contract-v1.md](plan/adr/0010-payload-contract-v1.md) — the JSON shape there is the spec; mirror field names, types, optionality exactly.
- pydantic v2: use `Field(..., description=...)` for everything that ships to JSON Schema. Use `model_config = ConfigDict(extra="forbid")` on `PayloadV1` to fail-loud on unknown fields (versioning is explicit).
- Canonical JSON encoding for `payload_hash`: `json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))`. Use sha256 from `hashlib`.
- The `image_request_payloads` table already exists from s02 (migration 002). Do not re-declare DDL.
- Resist the urge to add semantic validation beyond what ADR-0010 specifies (e.g. cross-field "if register is illustrated then camera_language must be ...") — that's prompt-template territory and lives in s06. The contract layer just shapes the data.
- The schema_export module should be a runnable `python -m app.payload.schema_export <out_path>` script; protect with `if __name__ == "__main__":`.

## Done signal

The subagent emits `<builder-os>COMPLETE</builder-os>` after `pytest slices/s04-payload-contract/tests` is fully green (DB-required tests skipped if no DATABASE_URL), `docs/payload-schema.v1.json` is regenerated and committed, no files under `paths_out_of_scope` were modified, and no test files under `slices/s04-payload-contract/tests/` were modified.
