"""In-memory asyncpg pool stub for hero-candidates endpoint tests."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Row:
    data: dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


@dataclass
class HeroFakeStore:
    idempotency: dict[str, uuid.UUID] = field(default_factory=dict)
    agent_runs: dict[uuid.UUID, dict[str, Any]] = field(default_factory=dict)
    payloads: list[dict[str, Any]] = field(default_factory=list)
    assets: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class HeroFakeConnection:
    def __init__(self, store: HeroFakeStore) -> None:
        self.store = store

    async def fetchrow(self, query: str, *args: Any) -> _Row | None:
        q = " ".join(query.split())
        if "FROM image_request_payloads WHERE idempotency_key" in q:
            key = str(args[0])
            run_id = self.store.idempotency.get(key)
            if run_id is None:
                return None
            return _Row({"agent_run_id": run_id})
        if "FROM image_request_payloads" in q and "agent_run_id = $1" in q:
            run_id = args[0]
            for row in self.store.payloads:
                if row.get("agent_run_id") == run_id:
                    return _Row({"payload": row.get("payload", {})})
            return None
        if "FROM external_media_assets" in q and "WHERE id = $1" in q:
            asset_id = args[0]
            for asset in self.store.assets:
                if asset["id"] == asset_id:
                    return _Row(
                        {
                            "id": asset["id"],
                            "status": asset.get("status"),
                            "agent_run_id": asset.get("agent_run_id"),
                            "site_id": asset.get("site_id"),
                            "metadata": asset.get("metadata", {}),
                        }
                    )
            return None
        if "FROM agent_runs WHERE id = $1" in q:
            run_id = args[0]
            row = self.store.agent_runs.get(run_id)
            if row is None:
                return None
            if "metadata" in q:
                return _Row(
                    {
                        "status": row["status"],
                        "finished_at": row.get("finished_at"),
                        "metadata": row.get("metadata", {}),
                    }
                )
            if "finished_at" not in q:
                return _Row({"status": row["status"]})
            return _Row({"status": row["status"], "finished_at": row.get("finished_at")})
        if "INSERT INTO agent_runs" in q and "RETURNING id" in q:
            run_id = uuid.uuid4()
            meta = json.loads(args[1]) if isinstance(args[1], str) else args[1]
            self.store.agent_runs[run_id] = {
                "id": run_id,
                "run_type": args[0],
                "status": "running",
                "metadata": meta,
                "finished_at": None,
            }
            return _Row({"id": run_id})
        if "INSERT INTO external_media_assets" in q and "RETURNING id" in q:
            asset_id = uuid.uuid4()
            meta = json.loads(args[4]) if isinstance(args[4], str) else args[4]
            self.store.assets.append(
                {
                    "id": asset_id,
                    "agent_run_id": args[0],
                    "site_id": args[1],
                    "status": "pending",
                    "metadata": meta,
                    "created_ord": len(self.store.assets),
                }
            )
            return _Row({"id": asset_id})
        if "INSERT INTO image_request_payloads" in q and "RETURNING id" in q:
            payload_id = uuid.uuid4()
            self.store.payloads.append(
                {
                    "id": payload_id,
                    "agent_run_id": args[0],
                    "idempotency_key": args[4],
                }
            )
            self.store.idempotency[str(args[4])] = args[0]
            return _Row({"id": payload_id})
        if "INSERT INTO tool_calls" in q and "RETURNING id" in q:
            tc_id = len(self.store.tool_calls) + 1
            self.store.tool_calls.append(
                {
                    "id": tc_id,
                    "run_id": args[0],
                    "cost_cents": args[6],
                }
            )
            return _Row({"id": tc_id})
        if "UPDATE agent_runs" in q and "RETURNING cost_cents" in q:
            run_id = args[0]
            row = self.store.agent_runs.get(run_id)
            if row is not None:
                total = sum(
                    tc.get("cost_cents", 0)
                    for tc in self.store.tool_calls
                    if tc.get("run_id") == run_id
                )
                row["cost_cents"] = total
                row["finished_at"] = row.get("finished_at") or "now"
                return _Row({"cost_cents": total})
            return _Row({"cost_cents": 0})
        return None

    async def fetch(self, query: str, *args: Any) -> list[_Row]:
        q = " ".join(query.split())
        if "FROM external_media_assets" in q and "agent_run_id = $1" in q:
            run_id = args[0]
            rows = [a for a in self.store.assets if a["agent_run_id"] == run_id]
            rows.sort(key=lambda r: r.get("created_ord", 0))
            return [
                _Row(
                    {
                        "r2_url": r.get("r2_url"),
                        "r2_key": r.get("r2_key"),
                        "status": r.get("status"),
                        "metadata": r.get("metadata", {}),
                    }
                )
                for r in rows
            ]
        return []

    async def execute(self, query: str, *args: Any) -> str:
        q = " ".join(query.split())
        if q.startswith("UPDATE agent_runs"):
            run_id = args[0]
            row = self.store.agent_runs.get(run_id)
            if row is None:
                return "UPDATE 0"
            if "finished_at = now()" in q or "finished_at = COALESCE" in q:
                row["finished_at"] = "now"
            if "SET status = $2" in q:
                row["status"] = args[1]
            if "metadata = COALESCE" in q and len(args) >= 3:
                patch = json.loads(args[2]) if isinstance(args[2], str) else args[2]
                row["metadata"] = {**row.get("metadata", {}), **patch}
            return "UPDATE 1"
        if "UPDATE external_media_assets" in q:
            asset_id = args[0]
            for asset in self.store.assets:
                if asset["id"] != asset_id:
                    continue
                if "status = 'superseded'" in q:
                    asset["status"] = "superseded"
                    replaced_by = str(args[1])
                    asset["metadata"] = {
                        **asset.get("metadata", {}),
                        "replaced_by": replaced_by,
                    }
                    return "UPDATE 1"
                if "status = 'generated'" in q:
                    asset["status"] = "generated"
                    asset["width"] = args[1]
                    asset["height"] = args[2]
                    if len(args) >= 6 and "metadata ||" in q:
                        patch = json.loads(args[5]) if isinstance(args[5], str) else args[5]
                        asset["metadata"] = {**asset.get("metadata", {}), **patch}
                    return "UPDATE 1"
                if "status = 'uploaded'" in q:
                    asset["status"] = "uploaded"
                    asset["r2_key"] = args[1]
                    asset["r2_url"] = args[2]
                    return "UPDATE 1"
                if "status = 'failed'" in q:
                    asset["status"] = "failed"
                    if len(args) >= 2:
                        patch = json.loads(args[1]) if isinstance(args[1], str) else args[1]
                        asset["metadata"] = {**asset.get("metadata", {}), **patch}
                    return "UPDATE 1"
                if "metadata = COALESCE" in q or "metadata = metadata ||" in q:
                    patch = json.loads(args[1]) if isinstance(args[1], str) else args[1]
                    asset["metadata"] = {**asset.get("metadata", {}), **patch}
                    return "UPDATE 1"
            return "UPDATE 0"
        if q.startswith("DELETE FROM agent_runs"):
            self.store.agent_runs.pop(args[0], None)
            return "DELETE 1"
        return "UPDATE 0"


class HeroFakePool:
    def __init__(self, store: HeroFakeStore | None = None) -> None:
        self.store = store or HeroFakeStore()

    @asynccontextmanager
    async def acquire(self):
        yield HeroFakeConnection(self.store)


def seed_uploaded_hero_assets(
    store: HeroFakeStore,
    run_id: uuid.UUID,
    *,
    count: int = 3,
) -> None:
    for i in range(count):
        store.assets.append(
            {
                "id": uuid.uuid4(),
                "agent_run_id": run_id,
                "status": "uploaded",
                "r2_key": f"hero-candidates/{run_id}/{i}.png",
                "r2_url": f"https://r2.example/hero-candidates/{run_id}/{i}.png",
                "metadata": {
                    "variant_index": i,
                    "tone_angle": ["search", "story", "offer"][i],
                    "headline": f"Headline {i}",
                },
                "created_ord": i,
            }
        )
