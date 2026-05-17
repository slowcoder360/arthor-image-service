"""Resolve PayloadV1 → StyleProfile (ADR-0009)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Protocol

from app.payload.models import PayloadV1
from app.style.defaults import (
    DEFAULT_COMPOSITION,
    DEFAULT_DO_NOT,
    DEFAULT_LIGHTING_BY_REGISTER,
    INDUSTRY_DO_NOT_EXTENSIONS,
)
from app.style.profile import StyleProfile


class MoodLLMClient(Protocol):
    async def expand_mood(
        self, industry: str, location: dict[str, Any], value_prop: str
    ) -> list[str]:
        ...


def _strip_present(value: str | None) -> bool:
    return bool(value is not None and value.strip())


def _matched_industry_keys(industry: str) -> list[str]:
    low = industry.lower()
    return sorted(k for k in INDUSTRY_DO_NOT_EXTENSIONS if k in low)


def _build_do_not(payload: PayloadV1) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def extend(items: list[str]) -> None:
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)

    extend(list(payload.brand_voice.do_not))
    extend(list(payload.style_profile_hint.do_not))
    extend(list(DEFAULT_DO_NOT))
    for key in _matched_industry_keys(payload.business.industry):
        extend(list(INDUSTRY_DO_NOT_EXTENSIONS[key]))
    return out


def _resolve_mood_without_llm(payload: PayloadV1) -> list[str]:
    hint = payload.style_profile_hint
    if hint.era_mood is not None and hint.era_mood.strip():
        return [hint.era_mood.strip()]
    if payload.brand_voice.tone.strip():
        return [payload.brand_voice.tone.strip()]
    return ["approachable", "credible"]


def _mood_fallback_triggered(payload: PayloadV1) -> bool:
    hint = payload.style_profile_hint
    mood_missing = hint.era_mood is None or not str(hint.era_mood).strip()
    tone_blank = not payload.brand_voice.tone.strip()
    short_vp = len(payload.business.value_prop) < 50
    return mood_missing and tone_blank and short_vp


async def _expand_mood_via_llm(
    payload: PayloadV1,
    client: MoodLLMClient | None,
) -> list[str]:
    location_dict = payload.location.model_dump(mode="json")
    if client is None:
        return ["approachable", "credible"]
    try:
        raw = await asyncio.wait_for(
            client.expand_mood(
                payload.business.industry,
                location_dict,
                payload.business.value_prop,
            ),
            timeout=2.0,
        )
    except (TimeoutError, asyncio.TimeoutError, Exception):
        return ["approachable", "credible"]
    cleaned = [str(x).strip() for x in raw if str(x).strip()]
    return cleaned[:5] if cleaned else ["approachable", "credible"]


async def resolve_style_profile(
    payload: PayloadV1,
    *,
    mood_llm_client: MoodLLMClient | None = None,
) -> StyleProfile:
    bv = payload.brand_visual
    hint = payload.style_profile_hint
    register = bv.register_default

    lighting = (
        hint.lighting.strip()
        if _strip_present(hint.lighting)
        else DEFAULT_LIGHTING_BY_REGISTER[register]
    )

    composition = (
        list(hint.composition_rules)
        if hint.composition_rules
        else list(DEFAULT_COMPOSITION)
    )

    camera_language = (
        hint.camera_language.strip()
        if _strip_present(hint.camera_language)
        else "35mm environmental, shallow depth-of-field"
    )

    color_grading = (
        hint.color_grading.strip()
        if _strip_present(hint.color_grading)
        else "natural, true-to-life saturation"
    )

    must_include = list(hint.must_include)
    do_not = _build_do_not(payload)

    used_llm_fallback = False
    if _mood_fallback_triggered(payload):
        used_llm_fallback = True
        mood = await _expand_mood_via_llm(payload, mood_llm_client)
    else:
        mood = _resolve_mood_without_llm(payload)

    return StyleProfile(
        id=uuid.uuid4(),
        palette=bv.palette,
        lighting=lighting,
        register=register,
        composition=composition,
        camera_language=camera_language,
        color_grading=color_grading,
        mood=mood,
        do_not=do_not,
        must_include=must_include,
        resolver_used_llm_fallback=used_llm_fallback,
    )


def style_profile_to_metadata(profile: StyleProfile) -> dict[str, Any]:
    return {
        "id": str(profile.id),
        "palette": profile.palette.model_dump(mode="json"),
        "lighting": profile.lighting,
        "register": profile.register,
        "composition": list(profile.composition),
        "camera_language": profile.camera_language,
        "color_grading": profile.color_grading,
        "mood": list(profile.mood),
        "do_not": list(profile.do_not),
        "must_include": list(profile.must_include),
        "resolver_version": profile.resolver_version,
        "resolver_used_llm_fallback": profile.resolver_used_llm_fallback,
    }
