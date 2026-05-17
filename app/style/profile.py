"""Resolved StyleProfile model (ADR-0009)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, UUID4

from app.payload.models import Palette


class StyleProfile(BaseModel):
    """Immutable resolved style profile for a pack/run."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: UUID4
    palette: Palette
    lighting: str
    register_kind: Literal["photographic", "illustrated", "mixed"] = Field(
        ...,
        alias="register",
        serialization_alias="register",
    )
    composition: list[str]
    camera_language: str
    color_grading: str
    mood: list[str]
    do_not: list[str]
    must_include: list[str]
    resolver_version: Literal["1.0"] = "1.0"
    resolver_used_llm_fallback: bool = False

    @property
    def register(self) -> Literal["photographic", "illustrated", "mixed"]:
        return self.register_kind
