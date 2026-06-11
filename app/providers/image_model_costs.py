"""Reference costs for image generation models (USD cents per image at common hero sizes).

Update when bumping ``DEFAULT_MODEL_VERSION`` in provider modules.
Sources: OpenAI API pricing pages (Jun 2026), internal estimates for Gemini.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

QualityTier = Literal["low", "medium", "high"]
ProviderKey = Literal["openai_image", "google_nano_banana"]

# Hero-candidates output size (provider-supported 16:9).
HERO_DIMENSIONS: tuple[int, int] = (1536, 1024)


@dataclass(frozen=True)
class ModelCostRow:
    provider: ProviderKey
    model_id: str
    label: str
    quality: QualityTier
    cents_per_image: int
    notes: str
    in_service_default: bool = False


# OpenAI per-image $ at 1536×1024 from official tier tables (approximate cents).
# gemini-2.5-flash-image: internal parity estimate until Google publishes list pricing.
IMAGE_MODEL_COST_REFERENCE: tuple[ModelCostRow, ...] = (
    ModelCostRow(
        "openai_image",
        "gpt-image-1",
        "GPT Image 1 (legacy)",
        "medium",
        6,
        "Previous default. Deprecating ~Oct 2026.",
    ),
    ModelCostRow(
        "openai_image",
        "gpt-image-2",
        "GPT Image 2 (flagship)",
        "medium",
        6,
        "~$0.053/img at 1024² medium; scales with quality/resolution.",
        in_service_default=True,
    ),
    ModelCostRow(
        "openai_image",
        "gpt-image-1.5",
        "GPT Image 1.5",
        "medium",
        5,
        "~$0.05/img at 1536×1024 medium. Strong instruction following.",
    ),
    ModelCostRow(
        "openai_image",
        "gpt-image-1.5",
        "GPT Image 1.5",
        "high",
        20,
        "~$0.20/img at 1536×1024 high. Previous flagship tier.",
    ),
    ModelCostRow(
        "openai_image",
        "gpt-image-2",
        "GPT Image 2 (flagship)",
        "high",
        26,
        "~$0.26/img at 2K high. Best photorealism + prompt adherence.",
    ),
    ModelCostRow(
        "openai_image",
        "gpt-image-1-mini",
        "GPT Image 1 Mini",
        "medium",
        3,
        "Budget drafts; lower fidelity.",
    ),
    ModelCostRow(
        "google_nano_banana",
        "gemini-2.5-flash-image",
        "Gemini 2.5 Flash Image",
        "medium",
        6,
        "Default Google tier (nano-banana). Fast; variable industry fidelity.",
        in_service_default=True,
    ),
    ModelCostRow(
        "google_nano_banana",
        "gemini-3.1-flash-image",
        "Gemini 3.1 Flash Image",
        "medium",
        7,
        "Candidate upgrade — better instruction following; evaluate via A/B lab.",
    ),
)


def hero_triad_cost_cents(model_id: str, *, quality: QualityTier = "medium") -> int | None:
    """Estimated cost for 3 hero images at ``HERO_DIMENSIONS``."""
    for row in IMAGE_MODEL_COST_REFERENCE:
        if row.model_id == model_id and row.quality == quality:
            return row.cents_per_image * 3
    return None


def format_cost_table_markdown() -> str:
    lines = [
        "| Provider | Model | Quality | ¢/image (1536×1024 hero) | Notes |",
        "|----------|-------|---------|--------------------------|-------|",
    ]
    for row in IMAGE_MODEL_COST_REFERENCE:
        default = " **default**" if row.in_service_default else ""
        lines.append(
            f"| {row.provider} | `{row.model_id}` | {row.quality} | {row.cents_per_image} | "
            f"{row.notes}{default} |"
        )
    lines.append("")
    lines.append(f"Hero triad (×3) at medium: multiply ¢/image by 3.")
    return "\n".join(lines)
