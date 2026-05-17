"""Local conftest: put this slice's tests/ on sys.path so absolute imports
of `_*` helpers resolve under pytest's `--import-mode=importlib`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
