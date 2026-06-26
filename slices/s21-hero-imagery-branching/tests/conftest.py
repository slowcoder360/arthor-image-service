"""Local conftest: put this slice's tests/ on sys.path for `_layout_helpers` imports."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
