"""SQLite-backed memory service for conversations, tasks, and steps."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConversationRecord:
    conversation_id: str
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class MessageRecord:
    message_id: str
    conversation_id: str
    role: int
    content: str
    created_at: str


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    conversation_id: str
    task_status: int
    approval_status: int
    title: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class TaskStepRecord:
    step_id: str
    task_id: str
    sequence_number: int
    title: str
    status: str
    detail: str
    created_at: str
    updated_at: str


class MemoryService:
    """Persistence service backed by SQLite and memory-store migrations."""

    name = "memory"

    def __init__(self, database_path: str, migrations_path: Path) -> None:
        self._database_path = Path(database_path)
        self._migrations_path = migrations_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_name TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            migration_files = sorted(self._migrations_path.glob("*.sql"))
            for migration_file in migration_files:
                exists = connection.execute(
                    "SELECT 1 FROM schema_migrations WHERE migration_name = ?",
                    (migration_file.name,),
                ).fetchone()
                if exists:
                    continue

                connection.executescript(migration_file.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                    (migration_file.name,),
                )

            connection.commit()

    def upsert_conversation(self, conversation: ConversationRecord) -> ConversationRecord:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM conversations WHERE conversation_id = ?",
                (conversation.conversation_id,),
            ).fetchone()

            created_at = conversation.created_at
            if existing is not None:
                created_at = str(existing["created_at"])

            connection.execute(
                """
                INSERT INTO conversations (conversation_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(conversation_id)
                DO UPDATE SET title = excluded.title, updated_at = excluded.updated_at
                """,
                (
                    conversation.conversation_id,
                    conversation.title,
                    created_at,
                    conversation.updated_at,
                ),
            )
            connection.commit()

        return ConversationRecord(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            created_at=created_at,
            updated_at=conversation.updated_at,
        )

    def get_conversation(self, conversation_id: str) -> ConversationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT conversation_id, title, created_at, updated_at
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()
        if row is None:
            return None

        return ConversationRecord(
            conversation_id=str(row["conversation_id"]),
            title=str(row["title"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def list_conversations(self) -> list[ConversationRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT conversation_id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [
            ConversationRecord(
                conversation_id=str(row["conversation_id"]),
                title=str(row["title"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def add_message(self, message: MessageRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (message_id, conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.conversation_id,
                    message.role,
                    message.content,
                    message.created_at,
                ),
            )
            connection.commit()

    def list_messages(self, conversation_id: str) -> list[MessageRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT message_id, conversation_id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (conversation_id,),
            ).fetchall()

        return [
            MessageRecord(
                message_id=str(row["message_id"]),
                conversation_id=str(row["conversation_id"]),
                role=int(row["role"]),
                content=str(row["content"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

    def upsert_task(self, task: TaskRecord) -> TaskRecord:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM tasks WHERE task_id = ?",
                (task.task_id,),
            ).fetchone()

            created_at = task.created_at
            if existing is not None:
                created_at = str(existing["created_at"])

            connection.execute(
                """
                INSERT INTO tasks (task_id, conversation_id, task_status, approval_status, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id)
                DO UPDATE SET
                  conversation_id = excluded.conversation_id,
                  task_status = excluded.task_status,
                  approval_status = excluded.approval_status,
                  title = excluded.title,
                  updated_at = excluded.updated_at
                """,
                (
                    task.task_id,
                    task.conversation_id,
                    task.task_status,
                    task.approval_status,
                    task.title,
                    created_at,
                    task.updated_at,
                ),
            )
            connection.commit()

        return TaskRecord(
            task_id=task.task_id,
            conversation_id=task.conversation_id,
            task_status=task.task_status,
            approval_status=task.approval_status,
            title=task.title,
            created_at=created_at,
            updated_at=task.updated_at,
        )

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT task_id, conversation_id, task_status, approval_status, title, created_at, updated_at
                FROM tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            return None

        return TaskRecord(
            task_id=str(row["task_id"]),
            conversation_id=str(row["conversation_id"]),
            task_status=int(row["task_status"]),
            approval_status=int(row["approval_status"]),
            title=str(row["title"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def list_tasks(self) -> list[TaskRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT task_id, conversation_id, task_status, approval_status, title, created_at, updated_at
                FROM tasks
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [
            TaskRecord(
                task_id=str(row["task_id"]),
                conversation_id=str(row["conversation_id"]),
                task_status=int(row["task_status"]),
                approval_status=int(row["approval_status"]),
                title=str(row["title"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def upsert_task_step(self, step: TaskStepRecord) -> TaskStepRecord:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM task_steps WHERE step_id = ?",
                (step.step_id,),
            ).fetchone()

            created_at = step.created_at
            if existing is not None:
                created_at = str(existing["created_at"])

            connection.execute(
                """
                INSERT INTO task_steps (step_id, task_id, sequence_number, title, status, detail, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(step_id)
                DO UPDATE SET
                  sequence_number = excluded.sequence_number,
                  title = excluded.title,
                  status = excluded.status,
                  detail = excluded.detail,
                  updated_at = excluded.updated_at
                """,
                (
                    step.step_id,
                    step.task_id,
                    step.sequence_number,
                    step.title,
                    step.status,
                    step.detail,
                    created_at,
                    step.updated_at,
                ),
            )
            connection.commit()

        return TaskStepRecord(
            step_id=step.step_id,
            task_id=step.task_id,
            sequence_number=step.sequence_number,
            title=step.title,
            status=step.status,
            detail=step.detail,
            created_at=created_at,
            updated_at=step.updated_at,
        )
