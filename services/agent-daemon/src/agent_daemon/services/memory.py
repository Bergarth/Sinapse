"""SQLite-backed memory service for conversations and messages."""

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
