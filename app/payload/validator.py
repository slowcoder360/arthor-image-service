"""Strict-ish payload validation gate with structured reports."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.payload.models import PayloadV1


@dataclass(frozen=True, slots=True)
class ValidationReport:
    errors: list[dict[str, Any]]
    warnings: list[str]
    completeness_score: float


def validate_payload(raw: bytes | dict) -> tuple[PayloadV1 | None, ValidationReport]:
    """Parse and validate PayloadV1. Never raises except malformed JSON ``bytes``.

    Rules:
      * ``payload_version == \"2.0\"`` → structured errors, model not constructed.
      * ``payload_version == \"1.1\"`` → warn and coerce to ``1.0`` for validation.
      * ``completeness_score`` duplicates :meth:`PayloadV1.payload_completeness_score`.
    """
    warnings: list[str] = []

    if isinstance(raw, bytes):
        data_obj = json.loads(raw.decode("utf-8"))
    else:
        data_obj = copy.deepcopy(raw)

    if not isinstance(data_obj, dict):
        return None, ValidationReport(
            errors=[
                {
                    "type": "type_error",
                    "loc": ("__root__",),
                    "msg": "Top-level payload must be a JSON object.",
                    "input": data_obj,
                }
            ],
            warnings=warnings,
            completeness_score=0.0,
        )

    data = data_obj

    pv = data.get("payload_version")
    if pv == "2.0":
        err: dict[str, Any] = {
            "type": "version_error",
            "loc": ("payload_version",),
            "msg": (
                "payload_version='2.0' is not supported by PayloadV1 bindings; breaking "
                "releases require an explicit adapter (ADR-0010 versioning)."
            ),
            "input": pv,
        }
        return None, ValidationReport(errors=[err], warnings=warnings, completeness_score=0.0)

    if pv == "1.1":
        warnings.append(
            "payload_version='1.1' is treated as '1.0' for PayloadV1 until a typed 1.x release "
            "(ADR-0010 additive policy)."
        )
        data["payload_version"] = "1.0"

    try:
        payload = PayloadV1.model_validate(data)
    except PydanticValidationError as exc:
        return None, ValidationReport(
            errors=exc.errors(include_url=False, include_input=False),
            warnings=warnings,
            completeness_score=0.0,
        )

    return payload, ValidationReport(
        errors=[],
        warnings=warnings,
        completeness_score=payload.payload_completeness_score(),
    )
