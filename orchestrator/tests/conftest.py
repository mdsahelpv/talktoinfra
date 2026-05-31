"""Test configuration: in-memory SQLite + register shared package."""

import os
import sys
import importlib.util
from pathlib import Path

# Register shared package (PathFinder can't resolve it from sys.path
# due to editable-install path-hook placeholder entries).
_shared_root = Path(__file__).resolve().parent.parent.parent / "shared" / "shared"
_init_file = _shared_root / "__init__.py"
if _init_file.exists() and "shared" not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        "shared", str(_init_file),
        submodule_search_locations=[str(_shared_root)],
    )
    if _spec:
        _mod = importlib.util.module_from_spec(_spec)
        sys.modules["shared"] = _mod
        _spec.loader.exec_module(_mod)

os.environ.setdefault("TALKTOINFRA_DATABASE_URL", "sqlite+aiosqlite://")
