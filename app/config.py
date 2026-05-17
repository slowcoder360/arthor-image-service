"""Pydantic settings for arthor-image-service."""

from __future__ import annotations

import functools

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    fastapi_arthor_shared_secret: str | None = None
    inspector_admin_token: str | None = None
    r2_endpoint_url: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    max_concurrent_packs: int = 4
    palette_drift_threshold: float = 25.0
    cold_storage_interval_seconds: int = 86400
    log_level: str = "INFO"


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()
