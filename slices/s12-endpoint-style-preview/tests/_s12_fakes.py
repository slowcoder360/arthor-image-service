"""s12 fake provider — minimal, captures method/seed/prompt; can be set to fail."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FakeCall:
    method: str
    seed: int | None
    prompt: str | None


class FakeProvider:
    def __init__(
        self,
        name: str = "openai_image",
        model_version: str = "gpt-image-1",
        fail: bool = False,
    ):
        self.name = name
        self.supports_pack_consistent = False
        self.supports_reference_image = True
        self.model_version = model_version
        self.calls: list[FakeCall] = []
        self._fail = fail

    async def generate_single(self, **kwargs):
        self.calls.append(
            FakeCall(
                method="generate_single",
                seed=kwargs.get("seed"),
                prompt=str(kwargs.get("prompt", "")),
            )
        )
        if self._fail:
            try:
                from app.providers.openai_image import ProviderError  # type: ignore[import-not-found]
            except Exception:  # noqa: BLE001
                ProviderError = RuntimeError
            raise ProviderError("fake style-preview provider failure")
        try:
            from app.providers.protocol import ProviderResult  # type: ignore[import-not-found]
        except Exception:  # noqa: BLE001
            return {
                "image_bytes": b"\x89PNGfake",
                "width": 1024,
                "height": 1024,
                "seed": None,
                "provider": self.name,
                "model_version": self.model_version,
                "cost_cents": 1,
                "latency_ms": 1,
                "external_id": "x",
                "response_shape": {},
                "determinism_level": "best-effort",
            }
        return ProviderResult(
            image_bytes=b"\x89PNGfake",
            width=1024,
            height=1024,
            seed=None,
            provider=self.name,
            model_version=self.model_version,
            cost_cents=1,
            latency_ms=1,
            external_id="x",
            response_shape={},
            determinism_level="best-effort",
        )
