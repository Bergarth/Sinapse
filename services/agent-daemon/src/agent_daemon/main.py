"""Entry point for the agent daemon service.

No production agent behavior is implemented yet.
"""

from agent_daemon.health import health_check
from agent_daemon.services.executor import ExecutorService
from agent_daemon.services.memory import MemoryService
from agent_daemon.services.planner import PlannerService
from agent_daemon.services.workspace import WorkspaceService


def main() -> None:
    """Start the placeholder agent daemon."""
    planner = PlannerService()
    executor = ExecutorService()
    memory = MemoryService()
    workspace = WorkspaceService()

    # Placeholder startup hook to confirm module wiring.
    if health_check().status != "ok":
        raise SystemExit("Service health check failed.")

    print("agent-daemon started (placeholder mode)")
    print(f"planner={planner.name}")
    print(f"executor={executor.name}")
    print(f"memory={memory.name}")
    print(f"workspace={workspace.name}")


if __name__ == "__main__":
    main()
