"""Ensure project root is on sys.path when running from web/."""
from __future__ import annotations

import sys
from pathlib import Path

_web_dir = Path(__file__).resolve().parent
_root_dir = _web_dir.parent

for path in (_root_dir, _web_dir):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
