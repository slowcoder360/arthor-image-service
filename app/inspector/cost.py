"""Cost rollup queries for ``/inspector/cost`` (s15).

Uses ``tool_calls.cost_cents`` joined to ``agent_runs`` for time/site filters.

Per-slot-type rollup joins ``image_request_payloads`` and ``external_media_assets`` so
``metadata.slot_id`` can be matched against ``payload->'slots'`` for ``slot_kind``.

EXPLAIN rationale (per-slot): Prefer starting from indexed ``tool_calls`` + ``tool_calls(provider)``
(and ``tool_calls(run_id)`` FK) → ``agent_runs``, then join ``image_request_payloads`` /
``external_media_assets`` by ``agent_run_id`` so row expansion stays proportional to touched
runs. ``DISTINCT ON (tool_calls.id)`` collapses incidental many-to-many join fan-out before
aggregation by ``slot_kind``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class CostRow:
    agent_run_id: uuid.UUID
    cost_cents: int
    started_at: datetime | None


@dataclass(frozen=True)
class DailyCostRow:
    day: date
    cost_cents: int


@dataclass(frozen=True)
class SiteCostRow:
    site_id: uuid.UUID | None
    cost_cents: int


@dataclass(frozen=True)
class ProviderCostRow:
    provider: str | None
    cost_cents: int


@dataclass(frozen=True)
class SlotTypeCostRow:
    slot_kind: str | None
    cost_cents: int


def format_cents_as_dollars(cents: int) -> str:
    return f"${cents / 100:.2f}"


async def cost_per_run(
    pool,
    *,
    limit: int = 25,
    date_from: date | None,
    date_to: date | None,
    site_id: uuid.UUID | None,
    provider: str | None,
) -> list[CostRow]:
    """Aggregate tool-call spend per agent run, newest ``started_at`` first."""

    prov = _norm_text(provider)

    sql = """
        SELECT
          ar.id AS agent_run_id,
          COALESCE(SUM(tc.cost_cents), 0)::bigint AS cost_cents,
          ar.started_at AS started_at
        FROM agent_runs ar
        INNER JOIN tool_calls tc ON tc.run_id = ar.id
        WHERE ($4::uuid IS NULL OR ar.site_id = $4::uuid)
          AND ($5::text IS NULL OR tc.provider IS NOT DISTINCT FROM $5::text)
          AND ($2::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date >= $2::date)
          AND ($3::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date <= $3::date)
        GROUP BY ar.id, ar.started_at
        ORDER BY ar.started_at DESC NULLS LAST
        LIMIT $1::bigint
        """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, limit, date_from, date_to, site_id, prov)
    result: list[CostRow] = []
    for r in rows:
        cid = r["cost_cents"]
        result.append(
            CostRow(
                agent_run_id=r["agent_run_id"],
                cost_cents=int(cid),
                started_at=r["started_at"],
            )
        )
    return result


async def cost_per_day(
    pool,
    *,
    days: int = 30,
    site_id: uuid.UUID | None,
    provider: str | None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[DailyCostRow]:
    """Daily sums in UTC calendar days.

    When ``date_from`` / ``date_to`` are omitted, bounds are the trailing ``days``
    interval from ``now()`` (backward compatible). When either bound is supplied, bounds
    are applied as inclusive UTC calendar-day filters matching the other rollup queries.
    """

    prov = _norm_text(provider)

    trailing_sql = """
        SELECT
          day,
          SUM(daily)::bigint AS cost_cents
        FROM (
          SELECT
            (ar.started_at AT TIME ZONE 'utc')::date AS day,
            tc.cost_cents AS daily
          FROM tool_calls tc
          INNER JOIN agent_runs ar ON tc.run_id = ar.id
          WHERE ar.started_at >= $1::timestamptz
            AND ($2::uuid IS NULL OR ar.site_id = $2::uuid)
            AND ($3::text IS NULL OR tc.provider IS NOT DISTINCT FROM $3::text)
        ) AS d
        GROUP BY day
        ORDER BY day ASC
        """

    bounded_sql = """
        SELECT
          day,
          SUM(daily)::bigint AS cost_cents
        FROM (
          SELECT
            (ar.started_at AT TIME ZONE 'utc')::date AS day,
            tc.cost_cents AS daily
          FROM tool_calls tc
          INNER JOIN agent_runs ar ON tc.run_id = ar.id
          WHERE ($1::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date >= $1::date)
            AND ($2::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date <= $2::date)
            AND ($3::uuid IS NULL OR ar.site_id = $3::uuid)
            AND ($4::text IS NULL OR tc.provider IS NOT DISTINCT FROM $4::text)
        ) AS d
        GROUP BY day
        ORDER BY day ASC
        """

    async with pool.acquire() as conn:
        if date_from is None and date_to is None:
            since = datetime.now(timezone.utc) - timedelta(days=days)
            rows = await conn.fetch(trailing_sql, since, site_id, prov)
        else:
            rows = await conn.fetch(bounded_sql, date_from, date_to, site_id, prov)
    out: list[DailyCostRow] = []
    for r in rows:
        out.append(DailyCostRow(day=r["day"], cost_cents=int(r["cost_cents"])))
    return out


async def cost_per_site(
    pool,
    *,
    limit: int = 25,
    date_from: date | None,
    date_to: date | None,
    provider: str | None,
) -> list[SiteCostRow]:
    """Top ``limit`` sites by total tool-call cents in the filter window."""

    prov = _norm_text(provider)

    sql = """
        SELECT
          ar.site_id AS site_id,
          COALESCE(SUM(tc.cost_cents), 0)::bigint AS cost_cents
        FROM tool_calls tc
        INNER JOIN agent_runs ar ON tc.run_id = ar.id
        WHERE ($2::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date >= $2::date)
          AND ($3::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date <= $3::date)
          AND ($4::text IS NULL OR tc.provider IS NOT DISTINCT FROM $4::text)
        GROUP BY ar.site_id
        ORDER BY cost_cents DESC NULLS LAST, site_id DESC NULLS LAST
        LIMIT $1::bigint
        """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, limit, date_from, date_to, prov)
    out: list[SiteCostRow] = []
    for r in rows:
        out.append(SiteCostRow(site_id=r["site_id"], cost_cents=int(r["cost_cents"])))
    return out


async def cost_per_provider(
    pool,
    *,
    date_from: date | None,
    date_to: date | None,
    site_id: uuid.UUID | None,
) -> list[ProviderCostRow]:
    sql = """
        SELECT
          tc.provider AS provider,
          COALESCE(SUM(tc.cost_cents), 0)::bigint AS cost_cents
        FROM tool_calls tc
        INNER JOIN agent_runs ar ON tc.run_id = ar.id
        WHERE ($3::uuid IS NULL OR ar.site_id = $3::uuid)
          AND ($1::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date >= $1::date)
          AND ($2::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date <= $2::date)
        GROUP BY tc.provider
        ORDER BY cost_cents DESC NULLS LAST
        """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, date_from, date_to, site_id)
    out: list[ProviderCostRow] = []
    for r in rows:
        out.append(ProviderCostRow(provider=r["provider"], cost_cents=int(r["cost_cents"])))
    return out


async def cost_per_slot_type(
    pool,
    *,
    date_from: date | None,
    date_to: date | None,
    site_id: uuid.UUID | None,
    provider: str | None,
) -> list[SlotTypeCostRow]:
    prov = _norm_text(provider)

    sql = """
        SELECT
          agg.slot_kind AS slot_kind,
          COALESCE(SUM(agg.cost_cents), 0)::bigint AS cost_cents
        FROM (
          SELECT DISTINCT ON (tc.id)
            tc.cost_cents,
            elem->>'slot_kind' AS slot_kind
          FROM tool_calls tc
          INNER JOIN agent_runs ar ON tc.run_id = ar.id
          INNER JOIN image_request_payloads irp ON irp.agent_run_id = ar.id
          INNER JOIN external_media_assets ema ON ema.agent_run_id = ar.id
          CROSS JOIN LATERAL jsonb_array_elements(irp.payload->'slots') AS elem
          WHERE elem->>'slot_id' IS NOT NULL
            AND ema.metadata->>'slot_id' IS NOT NULL
            AND elem->>'slot_id' = ema.metadata->>'slot_id'
            AND ($3::uuid IS NULL OR ar.site_id = $3::uuid)
            AND ($4::text IS NULL OR tc.provider IS NOT DISTINCT FROM $4::text)
            AND ($1::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date >= $1::date)
            AND ($2::date IS NULL OR (ar.started_at AT TIME ZONE 'utc')::date <= $2::date)
          ORDER BY tc.id ASC, ema.id ASC
        ) AS agg
        WHERE agg.slot_kind IS NOT NULL AND length(trim(agg.slot_kind)) > 0
        GROUP BY agg.slot_kind
        ORDER BY cost_cents DESC NULLS LAST, slot_kind ASC
        """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, date_from, date_to, site_id, prov)
    out: list[SlotTypeCostRow] = []
    for r in rows:
        sk = r["slot_kind"]
        out.append(SlotTypeCostRow(slot_kind=sk, cost_cents=int(r["cost_cents"])))
    return out


def _norm_text(s: str | None) -> str | None:
    if s is None:
        return None
    t = str(s).strip()
    return None if not t else t

