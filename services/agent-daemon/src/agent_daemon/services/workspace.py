"""Workspace service placeholder.

Extension points:
- Workspace lifecycle management
- File operations and policy enforcement
"""


class WorkspaceService:
    """Minimal workspace stub with explicit extension seam."""

    name = "workspace"

    def prepare(self, workspace_id: str) -> None:
        """Workspace preparation placeholder."""
        _ = workspace_id
