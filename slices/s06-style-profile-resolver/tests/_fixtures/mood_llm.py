"""FakeMoodLLMClient for s06 resolver tests. Implements the MoodLLMClient Protocol shape."""

from __future__ import annotations

from typing import Any


class FakeMoodLLMClient:
    """Records calls to expand_mood and returns a configured response."""

    def __init__(
        self,
        response: list[str] | None = None,
        raise_exc: BaseException | None = None,
    ) -> None:
        self.response = response or ["calm", "trusted"]
        self.raise_exc = raise_exc
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def expand_mood(
        self, industry: str, location: dict[str, Any], value_prop: str
    ) -> list[str]:
        self.calls.append(("expand_mood", {"industry": industry, "value_prop": value_prop}))
        if self.raise_exc is not None:
            raise self.raise_exc
        return list(self.response)
