"""Make the repo root importable so scripts can `from src import ...`.

Import this first in every entry-point script:
    import _bootstrap  # noqa: F401
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
