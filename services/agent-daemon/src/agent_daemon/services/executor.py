"""Executor service placeholder.

Extension points:
- Tool routing
- Step execution and retries
"""


class ExecutorService:
    """Minimal executor stub with explicit extension seam."""

    name = "executor"

    def execute(self, steps: list[str]) -> list[str]:
        """Return placeholder execution outputs."""
        _ = steps
        return []
