"""s01 AC-3: Settings(BaseSettings) — fields, defaults, `.env`, `extra="ignore"`."""

from __future__ import annotations

from pathlib import Path

import pytest


# (field_name, expected_default, expected_type_hint_substring)
EXPECTED_FIELDS = [
    ("database_url", None, "str"),
    ("fastapi_arthor_shared_secret", None, "str"),
    ("inspector_admin_token", None, "str"),
    ("r2_endpoint_url", None, "str"),
    ("r2_access_key_id", None, "str"),
    ("r2_secret_access_key", None, "str"),
    ("r2_bucket", None, "str"),
    ("openai_api_key", None, "str"),
    ("google_api_key", None, "str"),
    ("max_concurrent_packs", 4, "int"),
    ("palette_drift_threshold", 25.0, "float"),
    ("cold_storage_interval_seconds", 86400, "int"),
    ("log_level", "INFO", "str"),
]


def _import_settings_class():
    try:
        from app.config import Settings  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-3: `app.config.Settings` must be importable; not yet implemented ({exc})"
        )
    return Settings


@pytest.mark.parametrize("field, default, _type_hint", EXPECTED_FIELDS)
def test_settings_field_present(field, default, _type_hint):
    Settings = _import_settings_class()
    instance = Settings()
    assert hasattr(instance, field), (
        f"AC-3: Settings must declare field '{field}' (per ADR-0002 documented env keys)"
    )


@pytest.mark.parametrize("field, default, _type_hint", EXPECTED_FIELDS)
def test_settings_field_default(field, default, _type_hint, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for var in {f.upper() for f, _, _ in EXPECTED_FIELDS}:
        monkeypatch.delenv(var, raising=False)
    Settings = _import_settings_class()
    instance = Settings()
    actual = getattr(instance, field)
    assert actual == default, (
        f"AC-3: Settings.{field} default must be {default!r}, got {actual!r}"
    )


def test_settings_extra_ignore_does_not_raise(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("THIS_KEY_IS_NOT_DECLARED_ON_SETTINGS", "value")
    Settings = _import_settings_class()
    Settings()


def test_settings_reads_dot_env(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgres://from-dotenv/db\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    Settings = _import_settings_class()
    instance = Settings()
    assert instance.database_url == "postgres://from-dotenv/db", (
        "AC-3: Settings must honor `.env` via env_file='.env'"
    )


def test_settings_get_settings_is_cached(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    try:
        from app.config import get_settings  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-3: `app.config.get_settings` must be importable; not yet implemented ({exc})"
        )
    a = get_settings()
    b = get_settings()
    assert a is b, "AC-3: get_settings() must be cached (functools.lru_cache)"
