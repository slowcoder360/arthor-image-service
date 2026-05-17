"""s11 fake provider — minimal copy of the s10 FakeProvider tailored to single-slot
regenerate tests (no pack-consistent batch path needed).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FakeCall:
    method: str
    slot_id: str | None
    seed: int | None
    has_reference: bool
    prompt: str | None = None


class FakeProvider:
    """Records every generate_single call. supports_pack_consistent=False because
    regenerate-slot only ever calls generate_single (per s11 AC-8).
    """

    def __init__(
        self,
        name: str = "openai_image",
        model_version: str = "gpt-image-1",
        single_failures: int = 0,
    ):
        self.name = name
        self.supports_pack_consistent = False
        self.supports_reference_image = True
        self.model_version = model_version
        self.calls: list[FakeCall] = []
        self._single_failures_remaining = single_failures

    async def generate_single(self, **kwargs):
        slot_id = kwargs.get("slot_id")
        seed = kwargs.get("seed")
        ref = kwargs.get("reference_images") or []
        self.calls.append(
            FakeCall(
                method="generate_single",
                slot_id=slot_id,
                seed=seed,
                has_reference=bool(ref),
                prompt=str(kwargs.get("prompt", "")),
            )
        )
        if self._single_failures_remaining > 0:
            self._single_failures_remaining -= 1
            try:
                from app.providers.openai_image import ProviderError  # type: ignore[import-not-found]
            except Exception:  # noqa: BLE001
                ProviderError = RuntimeError
            raise ProviderError(f"fake failure for slot={slot_id}")
        return _make_provider_result(self.name, self.model_version)


def _make_provider_result(provider: str, model_version: str):
    try:
        from app.providers.protocol import ProviderResult  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return {
            "image_bytes": b"\x89PNGfake",
            "width": 1024,
            "height": 1024,
            "seed": None,
            "provider": provider,
            "model_version": model_version,
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
        provider=provider,
        model_version=model_version,
        cost_cents=1,
        latency_ms=1,
        external_id="x",
        response_shape={},
        determinism_level="best-effort",
    )
