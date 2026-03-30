# agent-daemon

Python 3.13 scaffold for a future agent daemon service.

## What this contains

- Package scaffold using `src/` layout.
- Entry point (`agent_daemon.main:main`).
- Placeholder modules for:
  - planner
  - executor
  - memory
  - workspace service
- Placeholder health check.

No real agent logic is implemented yet.

## Project structure

```text
services/agent-daemon/
├── pyproject.toml
├── README.md
└── src/
    └── agent_daemon/
        ├── __init__.py
        ├── health.py
        ├── main.py
        └── services/
            ├── __init__.py
            ├── executor.py
            ├── memory.py
            ├── planner.py
            └── workspace.py
```

## Run notes

From repository root:

```bash
cd services/agent-daemon
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
agent-daemon
```

Expected output is placeholder startup logging and service names.

## Extension points

- Implement planning behavior in `PlannerService.plan`.
- Implement execution flow in `ExecutorService.execute`.
- Add persistence/retrieval in `MemoryService`.
- Add workspace lifecycle operations in `WorkspaceService`.
- Expand `health_check` for liveness/readiness/dependency checks.
