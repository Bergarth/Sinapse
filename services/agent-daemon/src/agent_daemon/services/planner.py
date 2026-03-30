"""Planner service placeholder.

Extension points:
- Task decomposition
- Prioritization and scheduling
"""


class PlannerService:
    """Minimal planner stub with explicit extension seam."""

    name = "planner"

    def plan(self, request: str) -> list[str]:
        """Return a placeholder plan for future implementation."""
        _ = request
        return []
