"""JSON Schema exporter for PayloadV1 (ADR-0010 artifact)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.payload.models import PayloadV1


def export_json_schema(out_path: Path) -> None:
    """Emit JSON Schema Draft 2020-12-compatible document for PayloadV1."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    schema = PayloadV1.model_json_schema()
    out_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m app.payload.schema_export <out_path>", file=sys.stderr)
        sys.exit(1)
    export_json_schema(Path(sys.argv[1]))
