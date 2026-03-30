"""Runtime loading for the windows-operator package."""

from __future__ import annotations

import importlib
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_windows_operator_service_class() -> type:
    """Load the shared windows operator service class from the monorepo package."""

    repo_root = Path(__file__).resolve().parents[4]
    operator_src = repo_root / "packages" / "windows-operator" / "src"
    if str(operator_src) not in sys.path:
        sys.path.insert(0, str(operator_src))

    module = importlib.import_module("windows_operator")
    return module.WindowsOperatorService
