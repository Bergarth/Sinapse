# Implementation Audit

Audit date: 2026-03-30

Legend:
- **COMPLETE** = capability is implemented and wired end-to-end for its stated scope.
- **PARTIAL** = substantial implementation exists, but significant limitations/gaps remain.
- **PLACEHOLDER ONLY** = scaffold/stub exists with placeholder behavior, no real implementation.
- **MISSING** = no meaningful implementation found.

> Note: when docs and code differed, this audit used code as source of truth.

## 1) Desktop shell scaffold — **COMPLETE**

**Why**
- A WinUI 3 desktop shell project exists with app bootstrap, main window, views, and viewmodels wired.
- Project references generated gRPC client code from shared protobuf contracts.

**Supporting files**
- `apps/desktop-shell/src/DesktopShell/DesktopShell.csproj`
- `apps/desktop-shell/src/DesktopShell/App.xaml.cs`
- `apps/desktop-shell/src/DesktopShell/MainWindow.xaml`
- `apps/desktop-shell/src/DesktopShell/Views/ChatView.xaml`
- `apps/desktop-shell/src/DesktopShell/ViewModels/MainWindowViewModel.cs`

---

## 2) Shell-to-daemon connection — **COMPLETE**

**Why**
- Desktop shell opens a gRPC channel and calls daemon endpoints (health, conversation, messaging, settings, workspace, task, speech).
- Main window startup status and multiple feature workflows depend on this live connection service.

**Supporting files**
- `apps/desktop-shell/src/DesktopShell/Services/DaemonConnectionService.cs`
- `apps/desktop-shell/src/DesktopShell/ViewModels/MainWindowViewModel.cs`
- `apps/desktop-shell/src/DesktopShell/ViewModels/ChatViewModel.cs`
- `apps/desktop-shell/src/DesktopShell/ViewModels/TaskTimelineViewModel.cs`

---

## 3) Shared contracts/protobuf — **COMPLETE**

**Why**
- Shared protobuf contract defines DTOs/enums and full daemon service RPC surface.
- Both daemon and desktop shell load/use this same contract (`GrpcServices="Client"` in shell, dynamic runtime loading in daemon).

**Supporting files**
- `packages/contracts/src/sinapse/contracts/v1/contracts.proto`
- `apps/desktop-shell/src/DesktopShell/DesktopShell.csproj`
- `services/agent-daemon/src/agent_daemon/contracts_runtime.py`

---

## 4) Daemon gRPC API surface — **PARTIAL**

**Why**
- The daemon implements all RPCs declared in protobuf service.
- However, at least one endpoint is explicit placeholder behavior (`ListArtifacts` returns `artifact-placeholder`), so API surface is present but not fully real.

**Supporting files**
- `packages/contracts/src/sinapse/contracts/v1/contracts.proto`
- `services/agent-daemon/src/agent_daemon/server.py`

---

## 5) Conversation persistence in SQLite — **COMPLETE**

**Why**
- SQLite-backed memory service applies migrations and persists conversations/messages.
- Send message flow writes user and assistant messages; list/get conversation reads persisted rows.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/services/memory.py`
- `packages/memory-store/migrations/0001_init.sql`
- `packages/memory-store/migrations/0005_message_model_metadata.sql`
- `services/agent-daemon/src/agent_daemon/server.py`

---

## 6) Task timeline event flow — **PARTIAL**

**Why**
- Daemon publishes task timeline events and streams them via `ObserveSystemState`; shell subscribes and renders timeline entries.
- Core execution path is still a placeholder task runner for many tasks (`_run_placeholder_task`), so flow is real but not fully production-grade for arbitrary tasks.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/server.py`
- `services/agent-daemon/src/agent_daemon/services/memory.py`
- `packages/contracts/src/sinapse/contracts/v1/contracts.proto`
- `apps/desktop-shell/src/DesktopShell/ViewModels/TaskTimelineViewModel.cs`
- `apps/desktop-shell/src/DesktopShell/Services/DaemonConnectionService.cs`

---

## 7) Workspace attachment with real persistence — **COMPLETE**

**Why**
- `AttachWorkspaceRoot` validates and resolves folder path, scans files, persists root metadata and file inventory in SQLite.
- Shell can attach folders and retrieve persisted workspace roots/files for a conversation.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/server.py`
- `services/agent-daemon/src/agent_daemon/services/memory.py`
- `packages/memory-store/migrations/0003_workspace.sql`
- `apps/desktop-shell/src/DesktopShell/ViewModels/ChatViewModel.cs`
- `apps/desktop-shell/src/DesktopShell/Services/DaemonConnectionService.cs`

---

## 8) Settings for model/provider/API keys — **PARTIAL**

**Why**
- Shell supports editing model mode/provider preference/providers/API key placeholders/search/speech settings.
- Daemon persists settings in SQLite and enforces validation.
- API keys are placeholders only (`placeholder://...` required), not real secret storage.

**Supporting files**
- `apps/desktop-shell/src/DesktopShell/ViewModels/SettingsViewModel.cs`
- `services/agent-daemon/src/agent_daemon/server.py`
- `services/agent-daemon/src/agent_daemon/services/memory.py`
- `packages/memory-store/migrations/0004_app_settings.sql`

---

## 9) Windows operator real read-only action — **COMPLETE**

**Why**
- Real read-only implementation enumerates visible top-level windows using Win32 APIs (`ctypes.windll.user32.EnumWindows`).
- Daemon calls this action from chat and task flows.
- Mutating actions remain intentionally blocked, but requested read-only capability exists.

**Supporting files**
- `packages/windows-operator/src/windows_operator/service.py`
- `services/agent-daemon/src/agent_daemon/server.py`
- `services/agent-daemon/src/agent_daemon/windows_operator_runtime.py`

---

## 10) Browser operator real read-only action — **COMPLETE**

**Why**
- Real read-only URL open is implemented using controlled HTTP fetch and visible-text extraction/summarization.
- Daemon invokes this from chat and task flows.
- Interactive/mutating browser actions are still blocked, but requested read-only capability exists.

**Supporting files**
- `packages/browser-operator/src/browser_operator/service.py`
- `services/agent-daemon/src/agent_daemon/server.py`
- `services/agent-daemon/src/agent_daemon/browser_operator_runtime.py`

---

## 11) Approval flow with persistence — **PARTIAL**

**Why**
- Approval gating exists: risk classification, waiting-for-approval task status, approval event emission, shell approve/deny/cancel actions.
- Approval records are persisted to SQLite (`approvals` table, `upsert_approval`).
- Runtime pending approvals are tracked in-memory for active waits; no daemon restart recovery/resume path for pending approval execution was found.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/server.py`
- `services/agent-daemon/src/agent_daemon/services/memory.py`
- `packages/memory-store/migrations/0006_approvals.sql`
- `apps/desktop-shell/src/DesktopShell/ViewModels/TaskTimelineViewModel.cs`
- `apps/desktop-shell/src/DesktopShell/Services/DaemonConnectionService.cs`

---

## 12) Real Ollama integration — **PARTIAL**

**Why**
- Real Ollama HTTP integration is implemented (`/api/tags` health/status and `/api/generate` completion).
- Router falls back to placeholder provider on failure/unavailability, so behavior is mixed real+fallback.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/services/model_router.py`
- `services/agent-daemon/src/agent_daemon/server.py`

---

## 13) Real web search integration — **COMPLETE**

**Why**
- Real web search adapter performs network requests to DuckDuckGo Instant Answer API and returns answer + sources.
- Daemon wires this into message handling when search intent is detected and search is enabled in settings.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/services/search_adapter.py`
- `services/agent-daemon/src/agent_daemon/server.py`
- `apps/desktop-shell/src/DesktopShell/ViewModels/SettingsViewModel.cs`

---

## 14) Real push-to-talk STT — **PARTIAL**

**Why**
- Shell has real push-to-talk capture path (start/stop microphone WAV recording), sends audio to daemon.
- Daemon uses real Whisper-based transcription if dependency is installed; otherwise returns explicit precondition failure.
- Therefore implementation is real but dependency-gated and not guaranteed available in all environments.

**Supporting files**
- `apps/desktop-shell/src/DesktopShell/Services/PushToTalkRecorderService.cs`
- `apps/desktop-shell/src/DesktopShell/ViewModels/ChatViewModel.cs`
- `apps/desktop-shell/src/DesktopShell/Services/DaemonConnectionService.cs`
- `services/agent-daemon/src/agent_daemon/speech_runtime.py`
- `services/agent-daemon/src/agent_daemon/server.py`

---

## 15) Real TTS replies — **PARTIAL**

**Why**
- Shell can request speech synthesis and play returned WAV bytes.
- Daemon uses `pyttsx3` for local TTS when installed; otherwise returns explicit precondition failure.
- Spoken replies are optional and settings-gated.

**Supporting files**
- `apps/desktop-shell/src/DesktopShell/Services/SpeechPlaybackService.cs`
- `apps/desktop-shell/src/DesktopShell/ViewModels/ChatViewModel.cs`
- `apps/desktop-shell/src/DesktopShell/Services/DaemonConnectionService.cs`
- `services/agent-daemon/src/agent_daemon/speech_runtime.py`
- `services/agent-daemon/src/agent_daemon/server.py`

---

## 16) Workspace file summarization — **PARTIAL**

**Why**
- Daemon can summarize/analyze attached workspace files specifically for `.frd` and `.zma` when asked.
- No generic file summarization pipeline for arbitrary workspace file types was found.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/server.py`
- `services/agent-daemon/src/agent_daemon/services/frd_zma_parser.py`
- `services/agent-daemon/src/agent_daemon/services/memory.py`

---

## 17) Real FRD parsing — **COMPLETE**

**Why**
- FRD parser reads file content, parses numeric rows, validates shape/ranges/order, and returns structured summary with warnings/errors.
- Daemon invokes parser over attached workspace FRD files and returns generated summary content.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/services/frd_zma_parser.py`
- `services/agent-daemon/src/agent_daemon/server.py`

---

## 18) Real ZMA parsing — **COMPLETE**

**Why**
- ZMA parser shares same real parsing/validation pipeline, with ZMA-specific column expectations and warnings.
- Daemon invokes parser over attached workspace ZMA files and returns generated summary content.

**Supporting files**
- `services/agent-daemon/src/agent_daemon/services/frd_zma_parser.py`
- `services/agent-daemon/src/agent_daemon/server.py`

---

## What is actually working now

- Desktop shell and daemon communicate over shared gRPC contracts.
- Conversations/messages, tasks, workspace roots/file inventories, app settings, and approval records persist in SQLite.
- Chat supports local model routing (with Ollama when reachable, placeholder fallback otherwise).
- Read-only Windows window enumeration and read-only browser URL open/summarization are implemented.
- Task/system event streaming updates timeline UI.
- Search, push-to-talk transcription, and spoken replies are implemented paths (with dependency/config gates for some runtime features).
- FRD/ZMA parsing and summary generation from attached workspace files are implemented.

## What still needs implementation

- Replace remaining placeholder behavior (notably artifact listing and placeholder task execution paths).
- Add robust approval recovery/resume semantics across daemon restarts for in-flight waits.
- Implement secure non-placeholder secret/key management if real provider keys are required.
- Broaden workspace summarization beyond FRD/ZMA and add richer analysis workflow.
- Expand operator capabilities beyond current read-only subset where product requirements allow.
