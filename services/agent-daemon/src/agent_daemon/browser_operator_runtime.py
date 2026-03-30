"""Runtime loading for the browser-operator package."""

from __future__ import annotations

import importlib
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_browser_operator_service_class() -> type:
    """Load the shared browser operator service class from the monorepo package."""

    repo_root = Path(__file__).resolve().parents[4]
    operator_src = repo_root / "packages" / "browser-operator" / "src"
    if str(operator_src) not in sys.path:
        sys.path.insert(0, str(operator_src))

    module = importlib.import_module("browser_operator")
    return module.BrowserOperatorService
