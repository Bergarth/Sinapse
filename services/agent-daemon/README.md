# agent-daemon

Python gRPC daemon implementing `sinapse.contracts.v1.DaemonContract`.

This README reflects the current implementation as of **2026-04-02**.

## Implemented API surface

- `HealthCheck`
- `StartConversation`
- `ListConversations`
- `GetConversation`
- `SendUserMessage`
- `GetAppSettings`
- `UpdateAppSettings`
- `TranscribeAudio`
- `SynthesizeSpeech`
- `AttachWorkspaceRoot`
- `GetConversationWorkspace`
- `StartTask`
- `ApproveStep`
- `CancelTask`
- `ResumeTask`
- `ListArtifacts`
- `ObserveSystemState` (server stream)

Also includes gRPC health service (`grpc.health.v1.Health/Check`) and correlation-id propagation.

## Runtime behavior highlights

- SQLite-backed persistence via `packages/memory-store` migrations.
- Model routing supports Ollama with placeholder fallback.
- Approval-gated task system with persisted approvals and pending-approval restoration at startup.
- Artifact persistence to disk + metadata in SQLite.
- Workspace intake/summarization for mixed file sets.
- FRD/ZMA parsing + first-pass crossover recommendations.
- Browser operator integration (read-only open URL plus controlled session task envelopes).
- Windows operator integration (enumerate windows + write-capable actions, Windows only).
- REW workflow support: attach/launch + import; export explicitly `not_yet_supported`.
- Communications workflow support: SMTP email and Slack webhook messaging, both approval-gated.

## Important gates and boundaries

- Secure secret storage requires Windows DPAPI (non-Windows fails closed for secret writes).
- STT requires `openai-whisper`; TTS requires `pyttsx3`.
- Email/messaging sends require valid communications config and `secret://local/...` refs.
- Browser upload/click/fill/collect-sources remain explicitly `NOT_YET_SUPPORTED`.
- Pending approvals are restored after restart, but interrupted task execution threads are not fully replayed.

## Local run

From repo root:

```bash
cd services/agent-daemon
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
agent-daemon
```

Override bind host/port:

```bash
AGENT_DAEMON_HOST=127.0.0.1 AGENT_DAEMON_PORT=50055 agent-daemon
```
