# Sinapse

Sinapse is a desktop-agent monorepo with a WinUI desktop shell, a Python gRPC daemon, shared protobuf contracts, and SQLite-backed local state.

This README reflects the code as of **2026-04-02**.

## Repository layout

- `apps/desktop-shell` — WinUI 3 shell that talks to the daemon over gRPC.
- `services/agent-daemon` — Python daemon implementing `DaemonContract`.
- `packages/contracts` — shared protobuf contracts.
- `packages/memory-store` — SQLite migrations + repository contract docs.
- `packages/windows-operator` — Windows desktop operator implementation.
- `packages/browser-operator` — controlled browser/read workflows.
- `docs` — architecture and supporting docs.

## What is currently implemented

- Shell ↔ daemon connection (`HealthCheck`, chat, tasks, workspace, settings, approvals, speech, stream observation).
- SQLite persistence for conversations/messages/tasks/task steps/workspace roots+files/settings/approvals/artifacts.
- Chat routing with Ollama support and explicit placeholder fallback.
- Workspace intake + summarization across mixed file types (`.frd`, `.zma`, `.txt`, `.md`, `.json`, `.csv`, image types, `.zip`).
- FRD/ZMA parsing and first-pass crossover suggestions.
- Approval-gated task flows with persisted approval records and restart-time pending approval restoration.
- Windows operator actions: enumerate windows, launch app, focus window, open file, type text (Windows only).
- Browser flows: read-only open URL summary + controlled session navigation/download/upload envelopes.
- REW workflow integration for launch/attach + import (export intentionally not yet supported).
- Communications workflows: approval-gated SMTP email send and Slack-webhook messaging send.
- Artifact persistence + `ListArtifacts` from stored records.

## Important dependency / environment gates

- **Windows required** for:
  - secure secret storage (DPAPI-backed `secret://local/...`),
  - Windows operator actions.
- **Ollama optional**: daemon falls back to placeholder responses if unavailable.
- **STT optional dependency**: `openai-whisper`.
- **TTS optional dependency**: `pyttsx3`.
- **Email/messaging** require configuration + valid secret references.
- **Browser interactive automation** is partially implemented: unsupported actions return typed `NOT_YET_SUPPORTED` responses.

## Getting started (daemon)

```bash
cd services/agent-daemon
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
agent-daemon
```

Default daemon address: `0.0.0.0:50051`.

## Documentation added for this truth pass

- `IMPLEMENTATION_AUDIT.md` — implementation reality by capability.
- `SMOKE_TEST_MATRIX.md` — flow-by-flow state (code present vs runnable vs manually verified).
