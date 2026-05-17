# ADR 0009: Style profile lifecycle + persistence

- Status: proposed
- Date: 2026-05-17

## Context

The packet calls StyleProfile "the consistency unlock — per-pack, not per-slot." Research subagent #10 confirmed that the synthesis docs do not define concrete `do_not` patterns or pro-pattern lists; the resolver must seed defaults from the packet + scorecard anchors and grow them via Justin's GUI iteration.

Per the intake decision (C), the style profile is **read-only in the GUI**; iteration on the style-profile resolver itself happens via Cursor edits in this repo. The GUI exists to fast-generate variants for verdict, not to author profiles.

## Options considered

- **A. Persist on `agent_runs.metadata.style_profile`** — single jsonb blob; one row per run; no extra table; trivially joinable.
- **B. New `style_profiles` table with FK from `agent_runs`** — queryable history of every distinct StyleProfile; over-engineered for v1 since each run resolves a fresh profile.
- **C. Pure in-memory; not persisted** — loses audit trail; GUI can't show "what did the model see."

## Decision

**Option A: persist resolved StyleProfile on `agent_runs.metadata.style_profile` jsonb.**

Lifecycle:

1. **Resolve** (deterministic, with one narrow LLM fallback):
   - Input: `payload.brand`, `payload.style_profile_hint`, `payload.slots[0].intent`, `payload.business`, `payload.location`.
   - Deterministic rules:
     - `palette`: copy from `payload.brand_visual.palette` verbatim.
     - `lighting`: copy `payload.style_profile_hint.lighting` if present; else look up by `payload.brand_visual.register_default` from `app/style/defaults.py` (table: `{photographic: "warm natural light, golden hour", illustrated: "even editorial flat lighting", mixed: "soft directional natural light"}`).
     - `register`: `payload.brand_visual.register_default` (required).
     - `composition`: copy `payload.style_profile_hint.composition_rules[]` joined; else default `["rule-of-thirds", "mid-distance framing", "negative space in safe_area"]`.
     - `camera_language`: copy `payload.style_profile_hint.camera_language` if present; else default per register.
     - `color_grading`: copy or default `"natural, true-to-life saturation"`.
     - `do_not`: union of `payload.brand_voice.do_not`, `payload.style_profile_hint.do_not`, the default seed list (see below), and any industry-specific extension (e.g. YMYL adds `"no patient faces", "no medical procedures shown explicitly"`).
     - `must_include`: copy `payload.style_profile_hint.must_include`; default empty.
   - **One LLM fallback:** if `payload.style_profile_hint.mood` is missing AND the brand voice tone is empty AND `payload.business.value_prop` is short (< 50 chars), call a small LLM to expand mood adjectives from `business + location + industry`. Cap at 1 call, $0.005 budget, 2-second timeout. Failure: use default `["approachable", "credible"]`.

2. **Default `do_not` seed list** (lives in `app/style/defaults.py`):
   ```python
   DEFAULT_DO_NOT = [
       "stock-photo aesthetic",
       "AI-uncanny faces",
       "synthetic AI guru aesthetic",
       "fake corporate office",
       "generic AI-influencer template",
       "saturated neon gradients",
       "warped or extra fingers",
       "broken/distorted text",
       "obvious AI watermarks",
       "fluorescent over-saturation",
   ]
   ```
   This grows via PRs after GUI iteration with Justin. No GUI editor in v1 (per intake decision C).

3. **Persist** on `agent_runs.metadata.style_profile`:
   ```json
   {
     "id": "<uuid>",
     "palette": { ... },
     "lighting": "warm natural light, golden hour",
     "register": "photographic",
     "composition": ["rule-of-thirds", "mid-distance framing"],
     "camera_language": "35mm environmental, shallow depth-of-field",
     "color_grading": "natural, true-to-life saturation",
     "mood": ["approachable", "expert", "calm"],
     "do_not": [ ... ],
     "must_include": [],
     "resolver_version": "1.0",
     "resolver_used_llm_fallback": false
   }
   ```

4. **Apply** in `app/style/prompt_builder.py`: every per-slot prompt is built deterministically as:
   ```
   [slot.subject.primary], [slot.subject.setting], [slot.copy_context.section_heading].
   Photographic register: [register]. [camera_language].
   Lighting: [lighting]. [composition.join(", ")]. [color_grading].
   Mood: [mood.join(", ")]. [must_include.join(", ")].
   Avoid: [do_not.join(", ")].
   Aspect: [dimensions.w]x[dimensions.h], safe area: [safe_area.mode] inset [safe_area.inset_pct]%.
   ```
   Same template every slot; the StyleProfile contributes the same language to every prompt. Returns prompt text + SHA-256 = `prompt_hash`.

5. **Validate** (deterministic, post-generation): extract dominant palette from generated image (Pillow `Image.quantize` + counting). Compare against `style_profile.palette` using CIE76 ΔE in LAB color space (`colormath` or hand-rolled). If avg ΔE > `settings.palette_drift_threshold` (default 25), set `external_media_assets.metadata.palette_drift = true` and `external_media_assets.metadata.palette_extracted = [hex_array]`. Does NOT fail the run; just surfaces in the GUI.

## Consequences

What gets easier:
- One jsonb blob per run; trivial to load + display in the GUI.
- Resolver changes ship as a single Cursor PR; old runs preserve their `style_profile` snapshot.
- Defaults are a single Python file Justin can edit + PR.

What gets harder:
- Querying for "which runs used register=photographic" requires a jsonb path expression (`agent_runs.metadata->'style_profile'->>'register'`). Add a GIN index if it becomes hot: `CREATE INDEX idx_agent_runs_style_register ON agent_runs ((metadata->'style_profile'->>'register'))`. Defer until needed.
- No cross-run style-profile dedup. Acceptable — each pack resolves fresh anyway.
