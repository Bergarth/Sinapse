# contracts

Shared, transport-level contracts between the desktop shell and agent daemon.

## Source of truth

All shared contracts live in a single protobuf file:

- `src/sinapse/contracts/v1/contracts.proto`

This file is the only source of truth for:

- task status enums
- approval status enums
- health status enums
- artifact/workspace/health/task DTOs
- daemon API method contracts

## Contract surface

The `DaemonContract` service defines:

- `HealthCheck`
- `StartConversation`
- `SendUserMessage`
- `StartTask`
- `ApproveStep`
- `CancelTask`
- `ResumeTask`
- `ListArtifacts`
- `ObserveSystemState` (server stream)

## How shell and daemon use these contracts

### Desktop shell

The shell acts as a client:

1. It loads generated client stubs from `contracts.proto`.
2. It sends typed requests for actions such as starting conversations/tasks and approving steps.
3. It subscribes to `ObserveSystemState` for streaming updates.
4. It renders UI using shared DTO/enums from generated types.

### Agent daemon

The daemon acts as a server:

1. It implements the `DaemonContract` RPC methods.
2. It accepts and validates incoming protobuf request messages.
3. It returns typed response DTOs and streams state events.
4. It reuses the same generated enums/DTOs to avoid drift with the shell.

## Notes

- No business logic should be placed in this package.
- This package contains only schema/contract definitions and related documentation.
- Language-specific code generation can be added later from this protobuf source.
