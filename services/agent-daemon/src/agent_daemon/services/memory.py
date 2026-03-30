"""Memory service placeholder.

Extension points:
- Persistence adapters
- Context retrieval and summarization
"""


class MemoryService:
    """Minimal memory stub with explicit extension seam."""

    name = "memory"

    def store(self, key: str, value: str) -> None:
        """Store operation placeholder."""
        _ = (key, value)

    def fetch(self, key: str) -> str | None:
        """Fetch operation placeholder."""
        _ = key
        return None
