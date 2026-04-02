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
- `docs` — architecture and release-candidate docs.

## Release-candidate status (clear categories)

### Implemented

- Shell ↔ daemon connection and startup status panel.
- Chat, task timeline, approvals, conversation persistence, artifact listing.
- Workspace intake/summarization and FRD/ZMA parsing.
- Windows operator actions (enumerate/launch/focus/open/type).
- Browser read/open-url path and workflow envelope.
- Email + messaging draft/review/send workflow plumbing.

### Runnable with config/dependencies

- Ollama local-model chat path.
- Secure secret-backed references (`secret://local/...`) when daemon runs on Windows.
- STT (`openai-whisper`) and TTS (`pyttsx3`).
- Email sending (SMTP settings + secret reference).
- Messaging sending (Slack webhook secret reference).

### Manually verified

- See `SMOKE_TEST_MATRIX.md` for per-flow manual verification status.
- Use `docs/WINDOWS_SMOKE_TEST_CHECKLIST.md` for repeatable manual verification.

### Intentionally not yet supported

- Some browser interactive automations return explicit `NOT_YET_SUPPORTED`.
- REW export is intentionally not supported.

## First-run dependency checks

At shell startup, the daemon health payload now reports:

- daemon reachable,
- Ollama reachable,
- Windows operator availability,
- secure secret storage availability,
- optional STT availability,
- optional TTS availability,
- email configuration readiness,
- messaging configuration readiness.

If a gate is missing, status details are written in beginner-friendly, actionable language.

## Quick start

### Daemon

```bash
cd services/agent-daemon
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
agent-daemon
```

### Shell (Windows)

```powershell
cd apps/desktop-shell/src/DesktopShell
dotnet build
# run with Visual Studio/debug profile
```

## RC docs

- `SMOKE_TEST_MATRIX.md` — implemented vs runnable vs manually verified vs intentionally unsupported.
- `docs/WINDOWS_SMOKE_TEST_CHECKLIST.md` — manual smoke checklist + runner docs for Windows.
- `docs/RELEASE_READINESS_RC.md` — personal release-readiness notes.
- `IMPLEMENTATION_AUDIT.md` — implementation reality by capability.
