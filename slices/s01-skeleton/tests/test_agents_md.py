"""s01 AC-7: AGENTS.md exists and contains the user rule verbatim + module map."""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_MD = REPO_ROOT / "AGENTS.md"

USER_RULE_VERBATIM = (
    "only change what you need to change do not completely rewrite files. "
    "always ask permission before making changes that i did not ask for directly."
)

REQUIRED_MODULE_MAP_ENTRIES = [
    "app/payload/",
    "app/runs/",
    "app/style/",
    "app/storage/",
    "app/providers/",
    "app/routes/",
    "app/orchestration/",
    "app/inspector/",
    "app/jobs/",
    "db/migrations/",
]


def test_agents_md_exists():
    assert AGENTS_MD.exists(), (
        f"AC-7: AGENTS.md must exist at repo root ({AGENTS_MD}); not yet created"
    )


def test_agents_md_contains_user_rule_verbatim():
    if not AGENTS_MD.exists():
        pytest.fail("AC-7: AGENTS.md must exist; cannot check user rule")
    text = AGENTS_MD.read_text().lower()
    assert USER_RULE_VERBATIM.lower() in text, (
        "AC-7: AGENTS.md must contain the user rule verbatim "
        "('only change what you need to change ... directly.')"
    )


@pytest.mark.parametrize("entry", REQUIRED_MODULE_MAP_ENTRIES)
def test_agents_md_module_map_includes(entry):
    if not AGENTS_MD.exists():
        pytest.fail("AC-7: AGENTS.md must exist; cannot check module map")
    text = AGENTS_MD.read_text()
    assert entry in text, (
        f"AC-7: AGENTS.md module map must list '{entry}'"
    )
