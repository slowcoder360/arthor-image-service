"""s07 AC-1: R2Client.from_settings constructs when all four r2_* settings are set."""

from __future__ import annotations

import pytest

from _settings import FakeR2Settings, fully_unset


def _import_r2_client():
    try:
        from app.storage.r2 import R2Client  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: `app.storage.r2.R2Client` must be importable ({exc})")
    return R2Client


def test_from_settings_constructs_when_all_set():
    R2Client = _import_r2_client()
    client = R2Client.from_settings(FakeR2Settings())
    assert client is not None, "AC-1: R2Client.from_settings must return a non-None client"


def test_from_settings_raises_configuration_error_when_any_missing():
    R2Client = _import_r2_client()
    try:
        from app.storage.r2 import ConfigurationError  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(f"AC-1: ConfigurationError must be importable from app.storage.r2 ({exc})")

    with pytest.raises(ConfigurationError):
        R2Client.from_settings(fully_unset())

    partial = FakeR2Settings(r2_bucket=None)
    with pytest.raises(ConfigurationError):
        R2Client.from_settings(partial)
