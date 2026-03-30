"""Health-check primitives for the agent daemon."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthStatus:
    """Represents a minimal health-check response."""

    status: str
    details: str


def health_check() -> HealthStatus:
    """Return a placeholder health status.

    Extension point:
    - Add downstream dependency checks.
    - Add liveness/readiness segmentation.
    """
    return HealthStatus(status="ok", details="placeholder health check")
