"""Shared import bootstrap so every dashboard module is importable standalone.

Streamlit can execute a page module directly on a deep-linked load/refresh
before the entrypoint's sys.path fix is in scope. Importing this module first
adds the repo root to sys.path, making `import dashboard.*` work without
operator-configured PYTHONPATH. Mirrors the fix added in v0.6.1.
"""

import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
