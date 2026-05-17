"""s01 AC-4: RuntimeServices dataclass — settings required, all else optional."""

from __future__ import annotations

import pytest


def _import_runtime_pieces():
    try:
        from app.config import Settings  # type: ignore[import-not-found]
        from app.runtime import RuntimeServices  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-4: `app.runtime.RuntimeServices` and `app.config.Settings` must be importable ({exc})"
        )
    return RuntimeServices, Settings


def test_runtime_services_constructs_with_only_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    RuntimeServices, Settings = _import_runtime_pieces()
    services = RuntimeServices(settings=Settings())
    assert services.settings is not None, (
        "AC-4: RuntimeServices.settings must be the only required field"
    )


def test_runtime_services_optional_fields_default_none_or_empty(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    RuntimeServices, Settings = _import_runtime_pieces()
    services = RuntimeServices(settings=Settings())
    assert getattr(services, "pool", "MISSING") is None, (
        "AC-4: RuntimeServices.pool must default to None"
    )
    assert getattr(services, "r2", "MISSING") is None, (
        "AC-4: RuntimeServices.r2 must default to None"
    )
    assert getattr(services, "asset_pack_semaphore", "MISSING") is None, (
        "AC-4: RuntimeServices.asset_pack_semaphore must default to None"
    )
    providers = getattr(services, "providers", "MISSING")
    assert providers is None or providers == {}, (
        "AC-4: RuntimeServices.providers must default to None or {}"
    )
    background_tasks = getattr(services, "background_tasks", "MISSING")
    assert background_tasks == [] or background_tasks is None, (
        "AC-4: RuntimeServices.background_tasks must default to [] (or None)"
    )


def test_runtime_services_is_a_dataclass():
    RuntimeServices, _ = _import_runtime_pieces()
    import dataclasses

    assert dataclasses.is_dataclass(RuntimeServices), (
        "AC-4: RuntimeServices must be a dataclass (per ADR-0002 thin-shell pattern)"
    )
