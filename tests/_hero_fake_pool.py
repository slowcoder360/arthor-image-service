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
        if "FROM agent_runs WHERE id = $1" in q and "finished_at" not in q:
            run_id = args[0]
            row = self.store.agent_runs.get(run_id)
            if row is None:
                return None
            return _Row({"status": row["status"]})
        if "FROM agent_runs WHERE id = $1" in q:
            run_id = args[0]
            row = self.store.agent_runs.get(run_id)
            if row is None:
                return None
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
                        "status": r.get("status"),
                        "metadata": r.get("metadata", {}),
                    }
                )
                for r in rows
            ]
        return []

    async def execute(self, query: str, *args: Any) -> None:
        q = " ".join(query.split())
        if q.startswith("UPDATE agent_runs"):
            run_id = args[0]
            row = self.store.agent_runs.get(run_id)
            if row is None:
                return
            if "finished_at = now()" in q:
                row["finished_at"] = "now"
            if "SET status = $2" in q:
                row["status"] = args[1]
            if "metadata = COALESCE" in q and len(args) >= 3:
                patch = json.loads(args[2]) if isinstance(args[2], str) else args[2]
                row["metadata"] = {**row.get("metadata", {}), **patch}
        elif "UPDATE external_media_assets" in q:
            asset_id = args[0]
            for asset in self.store.assets:
                if asset["id"] == asset_id:
                    patch = json.loads(args[1]) if isinstance(args[1], str) else args[1]
                    asset["metadata"] = {**asset.get("metadata", {}), **patch}
                    break
        elif q.startswith("DELETE FROM agent_runs"):
            self.store.agent_runs.pop(args[0], None)


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
                "r2_url": f"https://r2.example/hero-candidates/{run_id}/{i}.png",
                "metadata": {
                    "variant_index": i,
                    "tone_angle": ["search", "story", "offer"][i],
                    "headline": f"Headline {i}",
                },
                "created_ord": i,
            }
        )
