# Sinapse

Minimal monorepo scaffold for future implementation.

## Repository layout

- `apps/desktop-shell`: Desktop application shell host (UI container and app bootstrapping later).
- `services/agent-daemon`: Background daemon service for agent lifecycle and orchestration.
- `packages/contracts`: Shared contracts/types/interfaces between apps and services.
- `packages/memory-store`: Shared package for memory persistence abstractions and adapters.
- `tests`: Cross-package and integration test suites.
- `docs`: Project documentation and architecture notes.

## Status

Business logic is intentionally not implemented yet; this scaffold defines structure only.
