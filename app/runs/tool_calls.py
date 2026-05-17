"""Writers and JSON trim helpers for ``tool_calls`` (ADR-0004)."""

from __future__ import annotations

import uuid
from typing import Any

import asyncpg

_TOOL_CALL_STATUS = frozenset({"ok", "error", "skipped"})
_MAX_STRING_LEN = 256
_PRESERVE_LONG_STRING_KEYS = frozenset(
    {"prompt_hash", "provider", "model_version", "seed", "external_id"}
)


def _trim_string(key: str | None, value: str) -> str | dict[str, Any]:
    if key is not None and key in _PRESERVE_LONG_STRING_KEYS:
        return value
    if len(value) <= _MAX_STRING_LEN:
        return value
    return {"_trimmed": True, "_original_len": len(value)}


def _trim_any(key: str | None, value: Any) -> Any:
    if isinstance(value, dict):
        return _trim_mapping(value)
    if isinstance(value, list):
        return [_trim_any(None, item) for item in value]
    if isinstance(value, str):
        return _trim_string(key, value)
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return value


def _trim_mapping(data: dict[str, Any]) -> dict[str, Any]:
    return {k: _trim_any(k, v) for k, v in data.items()}


def trim_args(args: dict[str, Any]) -> dict[str, Any]:
    """Trim ``tool_calls.args`` jsonb per retention rules (ADR-0004 §6)."""
    return _trim_mapping(dict(args))


def trim_result(result: dict[str, Any]) -> dict[str, Any]:
    """Trim ``tool_calls.result`` jsonb per retention rules (ADR-0004 §6)."""
    return _trim_mapping(dict(result))


def _validate_tool_status(status: str) -> None:
    if status not in _TOOL_CALL_STATUS:
        raise ValueError(f"unsupported tool_calls.status: {status!r}")


async def insert_tool_call(
    pool: asyncpg.pool.Pool,
    *,
    run_id: uuid.UUID,
    tool_name: str,
    args: dict[str, Any],
    result: dict[str, Any],
    status: str,
    latency_ms: int,
    cost_cents: int,
    provider: str | None,
    model_version: str | None,
) -> int:
    """Persist one ``tool_calls`` row; FK column is ``run_id``."""
    _validate_tool_status(status)
    trimmed_args = trim_args(args)
    trimmed_result = trim_result(result)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tool_calls (
              run_id, tool_name, args, result, status, latency_ms,
              cost_cents, provider, model_version
            )
            VALUES (
              $1, $2, $3::jsonb, $4::jsonb, $5, $6,
              $7, $8, $9
            )
            RETURNING id
            """,
            run_id,
            tool_name,
            trimmed_args,
            trimmed_result,
            status,
            latency_ms,
            cost_cents,
            provider,
            model_version,
        )
    assert row is not None
    return int(row["id"])
