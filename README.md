# Sinapse

Minimal monorepo scaffold for future implementation.

## Repository layout

- `apps/desktop-shell`: Will host the desktop application shell, including the UI container and application bootstrapping in future layers.
- `services/agent-daemon`: Will run as the background daemon responsible for agent lifecycle management and orchestration.
- `packages/contracts`: Will define shared contracts, types, and interfaces used between apps and services.
- `packages/memory-store`: Will provide shared memory persistence abstractions and storage adapters.
- `tests`: Will contain cross-package and integration test suites as implementation is added.
- `docs`: Contains project documentation and architecture notes.

## Status

This repository is still scaffold-only. No business logic has been implemented yet.
