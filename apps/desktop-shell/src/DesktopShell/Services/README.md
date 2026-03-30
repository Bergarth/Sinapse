# Services

UI-side service adapters used by the desktop shell.

Current service:

- `DaemonConnectionService`: runs a gRPC health check to verify the shell can reach `agent-daemon` and returns a beginner-friendly connection status model.

This is intentionally limited to connectivity and health probing only (no AI/task features yet).
