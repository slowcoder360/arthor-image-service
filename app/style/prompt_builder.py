"""Named entrypoint aligned with ADR-0009; delegates to ``app.style.prompts``."""

from __future__ import annotations

from app.payload.models import PayloadV1
from app.style.profile import StyleProfile
from app.style.prompts import build_slot_prompt as _build_prompt


def build_slot_prompt(
    *,
    slot,
    style_profile: StyleProfile,
    payload: PayloadV1 | None = None,
) -> str:
    _ = payload
    return _build_prompt(style_profile, slot).text
