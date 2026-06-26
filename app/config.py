"""Pydantic settings for arthor-image-service."""

from __future__ import annotations

import functools
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    fastapi_arthor_shared_secret: str | None = None
    inspector_admin_token: str | None = None
    # R2 — canonical names; arthor-ai aliases resolved in ``_resolve_r2_aliases``.
    r2_endpoint_url: str | None = None
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    r2_bucket_name: str | None = None
    r2_public_url: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    max_concurrent_packs: int = 4
    palette_drift_threshold: float = 25.0
    cold_storage_interval_seconds: int = 86400
    log_level: str = "INFO"
    hero_prompt_improve_enabled: bool = False
    hero_prompt_improve_canary_pct: float = 0.0
    hero_prompt_improve_model: str = "gpt-4o-mini"
    hero_prompt_improve_timeout_seconds: float = 8.0
    hero_default_provider: str = "openai_image"
    openai_image_model: str = "gpt-image-2"
    openai_image_quality: str = "medium"
    hero_openai_image_quality: str = "high"
    google_image_model: str = "gemini-2.5-flash-image"
    hero_prompt_cache_enabled: bool = True
    layout_archetype_data_path: str | None = None

    @model_validator(mode="after")
    def _resolve_r2_aliases(self) -> Self:
        """Accept arthor-ai R2 env names (``R2_ACCOUNT_ID``, ``R2_BUCKET_NAME``)."""
        endpoint = self.r2_endpoint_url
        if not endpoint and self.r2_account_id:
            endpoint = f"https://{self.r2_account_id.strip()}.r2.cloudflarestorage.com"
            object.__setattr__(self, "r2_endpoint_url", endpoint)
        bucket = self.r2_bucket or self.r2_bucket_name
        if bucket and not self.r2_bucket:
            object.__setattr__(self, "r2_bucket", bucket)
        return self


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
