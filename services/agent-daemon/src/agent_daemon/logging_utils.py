"""Structured logging helpers for agent-daemon."""

from __future__ import annotations

import contextvars
import json
import logging
import uuid
from datetime import UTC, datetime

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id",
    default="",
)


def set_correlation_id(value: str | None) -> str:
    """Set and return a correlation id for the active request context."""

    correlation_id = value or str(uuid.uuid4())
    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str:
    """Get the active request correlation id."""

    return _correlation_id.get() or ""


class JsonFormatter(logging.Formatter):
    """Format log records as compact JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }
        if hasattr(record, "grpc_method"):
            payload["grpc_method"] = record.grpc_method
        if hasattr(record, "peer"):
            payload["peer"] = record.peer
        return json.dumps(payload, separators=(",", ":"))


def configure_logging() -> logging.Logger:
    """Configure root logging once and return service logger."""

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    return logging.getLogger("agent_daemon")
