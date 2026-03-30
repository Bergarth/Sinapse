# agent-daemon

Python 3.13 gRPC daemon service with the first real API surface wired from shared contracts.

## Implemented surface

The service implements `sinapse.contracts.v1.DaemonContract` from `packages/contracts/src/sinapse/contracts/v1/contracts.proto` with production-backed persistence and first real task handlers for:

- `StartConversation`
- `SendUserMessage`
- `StartTask`
- `ApproveStep`
- `CancelTask`
- `ResumeTask`
- `ListArtifacts` (backed by persisted artifact records)
- `ObserveSystemState` (server stream)

Also included:

- `HealthCheck` method on the daemon contract
- Standard gRPC health service (`grpc.health.v1.Health/Check`)
- Structured JSON logging
- Correlation id propagation via `x-correlation-id` metadata

## Local run

From repo root:

```bash
cd services/agent-daemon
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
agent-daemon
```

Default bind address is `0.0.0.0:50051`.

Override with env vars:

```bash
AGENT_DAEMON_HOST=127.0.0.1 AGENT_DAEMON_PORT=50055 agent-daemon
```

## Notes

- Contract Python stubs are generated at runtime from the shared proto using `grpc_tools.protoc`, so `packages/contracts` remains the source of truth.
- Generic/unmatched tasks now return explicit `NOT_YET_SUPPORTED` task results (with persisted artifacts) instead of fake placeholder progress.
