"""s04 AC-7 / AC-8: export_json_schema writes a valid JSON Schema 2020-12 doc."""

from __future__ import annotations

import json

import pytest


def test_export_json_schema_writes_valid_schema(tmp_path):
    try:
        from app.payload.schema_export import export_json_schema  # type: ignore[import-not-found]
    except ImportError as exc:
        pytest.fail(
            f"AC-7: `app.payload.schema_export.export_json_schema` must be importable ({exc})"
        )

    out_path = tmp_path / "schema.json"
    export_json_schema(out_path)
    assert out_path.exists(), "AC-7: export_json_schema must write a file at out_path"

    schema = json.loads(out_path.read_text())
    assert isinstance(schema, dict), "AC-7: exported file must parse as a JSON object"

    properties = schema.get("properties") or schema.get("$defs", {}).get("PayloadV1", {}).get(
        "properties"
    )
    assert properties, (
        "AC-7: exported schema must declare 'properties' for PayloadV1 (top-level or under $defs)"
    )
    payload_version = properties.get("payload_version", {})
    const = payload_version.get("const") or payload_version.get("enum")
    assert const == "1.0" or const == ["1.0"], (
        f"AC-7/AC-8: properties.payload_version must be const/enum '1.0', got {payload_version}"
    )
