# Windows Manual Smoke Test Checklist (Release Candidate)

Date: 2026-04-02

This checklist is for a **real Windows PC** and is intentionally manual. It does not broaden automation scope.

## Prerequisites

- Windows 11 or Windows 10 with desktop session.
- Python 3.13 installed.
- .NET SDK that can build WinUI 3 desktop projects.
- Repo cloned locally.
- Optional (for gated checks):
  - Ollama installed and runnable.
  - `openai-whisper` for STT.
  - `pyttsx3` for TTS.
  - SMTP account + credentials in secure secret storage.
  - Slack webhook URL in secure secret storage.

## Runner setup (Windows PowerShell)

### 1) Start daemon

```powershell
cd services/agent-daemon
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
agent-daemon
```

Expected: daemon starts on `0.0.0.0:50051` and stays running.

### 2) Start desktop shell (separate PowerShell)

```powershell
cd apps/desktop-shell/src/DesktopShell
dotnet build
# run from Visual Studio or preferred WinUI run profile
```

Expected: startup panel loads and shows dependency/status checks from daemon.

## Manual smoke checklist

Mark each item as PASS/FAIL with notes.

### A. First-run startup dependency checks

- [ ] Daemon reachable status is shown (connected/disconnected with actionable text).
- [ ] Ollama reachable status is shown.
- [ ] Windows operator availability status is shown.
- [ ] Secure secret storage availability status is shown.
- [ ] Optional STT dependency status is shown.
- [ ] Optional TTS dependency status is shown.
- [ ] Email configuration readiness status is shown.
- [ ] Messaging configuration readiness status is shown.

### B. Core flows

- [ ] Chat send/receive works (placeholder fallback acceptable).
- [ ] Conversation reload from sidebar works.
- [ ] Task start appears in timeline.
- [ ] Approval prompt can be approved/denied.
- [ ] Workspace root can be attached and listed.

### C. Dependency-gated flows (only when configured)

- [ ] Ollama response path works when Ollama is running.
- [ ] Push-to-talk STT works when `openai-whisper` is installed.
- [ ] Spoken replies work when `pyttsx3` is installed.
- [ ] Email draft/review/send works when SMTP config + secure secret are valid.
- [ ] Messaging draft/review/send works when Slack secret is valid.
- [ ] Windows operator actions work on Windows (enumerate/launch/focus/open/type).

### D. Intentionally not yet supported

- [ ] Browser interactive gaps return explicit `NOT_YET_SUPPORTED` messages.
- [ ] REW export gap returns explicit not-yet-supported message.

## Recording results

Use this format in your release notes:

- Flow:
- Result: PASS / FAIL
- Environment:
- Notes:
- Follow-up action:
