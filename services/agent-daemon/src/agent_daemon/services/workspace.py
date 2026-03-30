"""Workspace service scaffold.

This module intentionally contains placeholder-only types for:
- attaching one or more roots to a conversation
- selecting read-only versus read-write workspace mode
- exposing visible workspace roots to callers

No real filesystem mutation or policy enforcement is implemented yet.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class WorkspaceMode(StrEnum):
    """Conversation workspace access modes."""

    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


@dataclass(slots=True)
class WorkspaceRoot:
    """Represents a visible workspace root attached to a conversation."""

    root_id: str
    display_name: str
    root_path: str


@dataclass(slots=True)
class ConversationWorkspace:
    """Placeholder aggregate for conversation-scoped workspace attachment."""

    conversation_id: str
    mode: WorkspaceMode = WorkspaceMode.READ_ONLY
    roots: list[WorkspaceRoot] = field(default_factory=list)


class WorkspaceService:
    """Minimal workspace scaffold with explicit extension seams."""

    name = "workspace"

    def attach_roots(
        self,
        conversation_id: str,
        roots: list[WorkspaceRoot],
        mode: WorkspaceMode = WorkspaceMode.READ_ONLY,
    ) -> ConversationWorkspace:
        """Placeholder for workspace attachment workflow.

        TODO: persist `workspace_roots` records and mode policy once data layer exists.
        """
        return ConversationWorkspace(
            conversation_id=conversation_id,
            mode=mode,
            roots=list(roots),
        )

    def get_workspace(self, conversation_id: str) -> ConversationWorkspace:
        """Placeholder read path returning a first-time-user-friendly default state.

        TODO: load persisted `workspace_roots` and `workspace_files` references.
        """
        return ConversationWorkspace(conversation_id=conversation_id)
