# Sinapse

Cross-platform desktop-agent monorepo with a working Python daemon, shared contracts, and storage migrations.

## Repository layout

- `apps/desktop-shell`: Desktop shell app workspace (early-stage scaffolding).
- `services/agent-daemon`: gRPC daemon with conversation, tasks, workspace indexing, approvals, artifact persistence, and local speech paths.
- `packages/contracts`: Shared protobuf contracts used by shell/daemon/services.
- `packages/memory-store`: SQLite schema migrations and repository contract docs.
- `tests`: Cross-package and integration test area.
- `docs`: Contains project documentation and architecture notes.

## Status

Implemented today:

- Shared contract-driven daemon API (`HealthCheck`, conversations/messages, tasks, approvals, workspace root attachment, artifact listing, system stream).
- SQLite-backed persistence for conversations, messages, tasks, steps, workspace roots/files, app settings, approvals, and artifacts.
- Real read-only task handlers for browser open-url and Windows window enumeration.
- Real approval-gated Windows operator task handlers for safe write actions (launch app, focus window, open file, type text).
- Mixed speaker-workspace intake/summarization across FRD/ZMA, text/markdown/json/csv, zip inventories, and image metadata.
- First-pass crossover region ranking for FRD/ZMA workflows with transparent warnings and confidence scores.
- Approval-gated REW workflow task support (launch/attach + import) with explicit `not_yet_supported` export typing.
- Approval-gate persistence with restart recovery for pending approvals.
- Local secure API-key storage integration using Windows DPAPI-backed secret references.

Still in progress:

- Planner/executor expansion to support more task types.
- Desktop-shell feature completion and end-to-end UX polish.
