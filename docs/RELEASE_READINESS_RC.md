# Sinapse Release Readiness (Personal RC Notes)

Date: 2026-04-02

This document is a practical release-candidate snapshot for day-to-day personal use.

## 1) Prerequisites

### Required

- Windows machine for full shell + operator + secure secret storage experience.
- Python 3.13 for `agent-daemon`.
- .NET SDK / WinUI 3 toolchain for desktop shell.

### Optional but important

- Ollama for local-model responses.
- `openai-whisper` for STT.
- `pyttsx3` for TTS.
- SMTP credentials (stored as `secret://local/...`) for email sending.
- Slack webhook secret (stored as `secret://local/...`) for messaging sends.

## 2) How to run the shell

```powershell
cd apps/desktop-shell/src/DesktopShell
dotnet build
# run via Visual Studio/debug profile
```

The shell is designed to show startup dependency checks in the top status panel.

## 3) How to run the daemon

```powershell
cd services/agent-daemon
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
agent-daemon
```

Default endpoint: `http://127.0.0.1:50051` from shell perspective.

## 4) What works now (implemented)

- Shell ↔ daemon gRPC wiring and startup health/status pull.
- Chat flow with persistence.
- Task timeline and approval interactions.
- Workspace attachment + summary/intake scaffolding.
- Windows operator safe action set (Windows only).
- Browser read-oriented operations and controlled workflow envelopes.
- Email and messaging draft/review/send task paths.

## 5) What is dependency-gated

- Ollama path (falls back when unavailable).
- Secure secret storage (Windows-only DPAPI).
- STT (`openai-whisper`) and TTS (`pyttsx3`).
- Email send readiness (SMTP config + secret reference must exist).
- Messaging send readiness (Slack webhook secret must exist).

## 6) What is intentionally not yet supported

- Some browser interactive actions still return typed `NOT_YET_SUPPORTED` responses.
- REW export remains intentionally unsupported.
- This repo currently relies on manual smoke verification for release confidence.

## 7) RC usage guidance

Before each release-candidate run:

1. Start daemon.
2. Start shell.
3. Read startup dependency statuses.
4. Run `docs/WINDOWS_SMOKE_TEST_CHECKLIST.md` manually.
5. Update `SMOKE_TEST_MATRIX.md` with what was manually verified in that run.
