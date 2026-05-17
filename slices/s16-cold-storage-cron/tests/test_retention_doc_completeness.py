"""s16 AC-6: `docs/retention.md` documents the documented sections — parse
for the required keywords/phrases.
"""

from __future__ import annotations

import pathlib

import pytest


def test_retention_doc_contains_required_sections():
    doc_path = pathlib.Path("docs/retention.md")
    if not doc_path.exists():
        pytest.fail(
            f"AC-6: docs/retention.md must exist; not found at {doc_path.absolute()}"
        )
    content = doc_path.read_text().lower()

    required = ["30 days", "cold/", "recovery", "interval", "active assets"]
    missing = [needle for needle in required if needle not in content]
    assert not missing, (
        f"AC-6: docs/retention.md must mention all of {required!r}; missing: {missing!r}"
    )
