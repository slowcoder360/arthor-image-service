"""s01 AC-6: system.yaml validates against the arthor-systemmap schema (or shape)."""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_system_yaml() -> dict:
    path = REPO_ROOT / "system.yaml"
    if not path.exists():
        pytest.fail(
            f"AC-6: system.yaml must exist at repo root ({path}); not yet created"
        )
    try:
        import yaml
    except ImportError as exc:
        pytest.fail(f"pyyaml is not installed in the test environment: {exc}")
    with path.open() as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "AC-6: system.yaml must parse to a YAML mapping"
    return data


def test_system_yaml_required_minimum_fields():
    data = _load_system_yaml()
    assert data.get("name") == "arthor-image-service", (
        "AC-6: system.yaml `name` must equal 'arthor-image-service'"
    )
    assert data.get("kind") == "service", "AC-6: system.yaml `kind` must equal 'service'"
    assert data.get("language") == "python", (
        "AC-6: system.yaml `language` must equal 'python'"
    )
    assert data.get("runtime") == "fastapi", (
        "AC-6: system.yaml `runtime` must equal 'fastapi'"
    )
    owners = data.get("owners")
    assert isinstance(owners, list) and "justin" in owners, (
        "AC-6: system.yaml `owners` must be a list containing 'justin'"
    )
