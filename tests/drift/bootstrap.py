"""Test-local imports for existing generated declarations and accepted state helpers."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT, ROOT / "apps" / "control-plane", ROOT / "contracts" / "generated" / "1.0.0" / "python"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
