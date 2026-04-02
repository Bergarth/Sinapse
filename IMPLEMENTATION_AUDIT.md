# IMPLEMENTATION_AUDIT

Audit date: 2026-04-02

This pass reflects **current code behavior** in this repository. Where docs and code differed, code was treated as source of truth.

## Status legend

- **Implemented**: code path exists and is wired in runtime flow for the documented scope.
- **Implemented (dependency/config gated)**: code path exists but only runs when environment, OS, secrets, or optional dependencies are present.
- **Partial**: meaningful implementation exists, but important sub-flows are explicitly not yet supported.
- **Unverified in this pass**: not manually executed end-to-end during this documentation pass.

---

## 1) Shell ↔ daemon connection

**Status:** Implemented (unverified in this pass)

- The desktop shell creates a gRPC client to `DaemonContract`, defaults to `http://127.0.0.1:50051`, and calls `HealthCheck` during startup.
- Startup UI reflects daemon/environment capability information returned by the daemon.
- The shell also opens a long-lived `ObserveSystemState` stream for timeline updates.

---

## 2) Chat and persistence

**Status:** Implemented (unverified in this pass)

- `SendUserMessage` persists user + assistant messages to SQLite and returns the persisted conversation/message DTOs.
- Conversation list/get endpoints read from SQLite.
- Shell chat viewmodel can start/load conversations and display persisted history.

---

## 3) Settings and secret storage

**Status:** Implemented (dependency/config gated)

- Model/search/speech/communications settings are persisted in SQLite via `app_settings`.
- API/search/communications secret refs must use `secret://local/...` for secure mode.
- Secure secret writes use Windows DPAPI and fail closed on non-Windows hosts.
- Shell settings UI is wired to get/update daemon settings and API key entries.

---

## 4) Approvals and restart recovery

**Status:** Partial

- High-risk task steps create persisted approval records and emit approval-required timeline events.
- Shell can approve/deny/cancel through gRPC.
- On daemon startup, pending approvals are restored into in-memory wait structures.
- **Limitation:** daemon does not resume previously interrupted execution threads after restart; persisted pending approvals are visible/reconcilable, but in-flight task execution is not fully replayed.

---

## 5) Ollama path

**Status:** Implemented (dependency/config gated)

- Router probes Ollama (`/api/tags`) and can generate responses (`/api/generate`).
- If Ollama is unavailable or errors, daemon falls back to built-in placeholder provider with explicit fallback text.

---

## 6) STT/TTS

**Status:** Implemented (dependency/config gated)

- Shell supports push-to-talk recording and sends WAV to daemon.
- Daemon STT uses `openai-whisper` if installed; otherwise returns explicit unavailable guidance.
- Daemon TTS uses `pyttsx3` if installed; otherwise returns explicit unavailable guidance.
- Shell can request synthesis and play WAV bytes.

---

## 7) Windows operator read and write actions

**Status:** Implemented (dependency/config gated)

- Read action: enumerate visible top-level windows via Win32 APIs.
- Write actions implemented: launch app, focus window, open file, type text.
- Write actions are routed through approval-gated task flows.
- Entire operator capability is gated to Windows runtime.

---

## 8) Browser workflows

**Status:** Partial (dependency/config gated by network/runtime)

- Read-only open URL is implemented via controlled HTTP fetch + visible-text summary extraction.
- Session workflow scaffolding exists for open session, navigate, read, download, upload.
- Download path writes artifacts; upload/click/fill/collect-sources explicitly return typed `NOT_YET_SUPPORTED` for unsupported automation.

---

## 9) Workspace intake and summarization

**Status:** Implemented (unverified in this pass)

- Workspace roots attach with path validation + file inventory persisted to SQLite.
- Intake supports FRD/ZMA/text/markdown/json/csv/images/zip classification with warnings.
- Workspace summary includes counts by type, samples, and zip inventory previews.

---

## 10) FRD/ZMA analysis

**Status:** Implemented (unverified in this pass)

- FRD and ZMA parsers read numeric tables, validate shape/ranges/order, and report warnings/errors.
- Chat/task flows invoke analysis over attached workspace files.

---

## 11) Crossover suggestions

**Status:** Implemented (unverified in this pass)

- Daemon computes first-pass crossover region rankings from parsed FRD/ZMA summaries.
- Output includes score/confidence/reasoning and warning context.

---

## 12) REW workflow

**Status:** Partial (dependency/config gated)

- Flow supports attach-or-launch REW, import FRD/ZMA (including controlled extraction from zip), and persisted workflow artifacts.
- Export automation intentionally returns typed `not_yet_supported`.
- Requires Windows operator availability and local REW executable accessibility.

---

## 13) Email workflow

**Status:** Implemented (dependency/config gated)

- Daemon drafts email artifact, requests approval, and sends via SMTP when configured.
- Supports workspace file attachments.
- Requires SMTP host/from/user and `secret://local/...` password ref that resolves in local secret store.

---

## 14) Messaging workflow

**Status:** Implemented (dependency/config gated)

- Daemon drafts messaging artifact, requests approval, and sends via Slack webhook.
- Current provider path is `slack-webhook`; other providers return explicit `NOT_YET_SUPPORTED`.
- Requires `secret://local/...` webhook ref.

---

## 15) Artifact listing

**Status:** Implemented (unverified in this pass)

- Task handlers persist artifacts to disk + SQLite metadata.
- `ListArtifacts` returns persisted artifact rows for a task (not placeholder).

---

## Summary: implemented now vs still unverified

### Truly implemented now (code present and wired)

- Shell/daemon gRPC integration, health checks, and system-state streaming.
- SQLite-backed persistence for conversations/messages/tasks/steps/workspaces/settings/approvals/artifacts.
- Approval-gated operator/task workflows with persisted approval records.
- Ollama + placeholder model routing.
- Workspace intake + FRD/ZMA parsing + crossover suggestion flow.
- REW/email/messaging/browser workflow handlers with explicit typed not-yet-supported boundaries where applicable.

### Still dependency-gated or environment-gated

- Windows-only paths: secure secret storage and windows operator actions.
- Ollama availability.
- STT (`openai-whisper`) and TTS (`pyttsx3`) optional dependencies.
- Email/messaging depend on valid communications config + secrets.

### Still partial or not fully end-to-end

- Browser interactive automation (upload/click/fill/collect sources) remains explicitly not yet supported.
- REW export automation remains not yet supported.
- Restart recovery restores pending approvals but does not fully replay interrupted in-flight execution threads.

### Manual verification state for this pass

- This was a **code truth pass**; flows were audited from implementation and wiring.
- End-to-end manual verification was **not** performed in this pass.
