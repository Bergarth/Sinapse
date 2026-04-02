# SMOKE_TEST_MATRIX

Date: 2026-04-02

This matrix is a **truth pass from code**, not a full manual QA run.

Definitions used:
- **Code present only**: wired in code, but would not run successfully without missing major runtime requirements.
- **Runnable with config/dependencies**: implementation appears executable when required OS/dependencies/config are provided.
- **Manually verified**: executed end-to-end by a human in this pass.
- **Not yet verified**: not manually executed in this pass.

| User-visible flow | Code present only | Runnable with config/dependencies | Manually verified | Not yet verified | Notes |
|---|---|---|---|---|---|
| Shell ↔ daemon connection |  | ✅ |  | ✅ | Shell gRPC client + daemon health/system-state endpoints are wired. |
| Chat and persistence |  | ✅ |  | ✅ | Message send/start/load paths persist in SQLite. |
| Settings and secret storage |  | ✅ |  | ✅ | Settings persistence runs cross-platform; secure secret writes require Windows DPAPI. |
| Approvals and restart recovery |  | ✅ |  | ✅ | Pending approvals restore on startup; full interrupted task replay remains partial. |
| Ollama path |  | ✅ |  | ✅ | Works when Ollama is reachable; fallback provider used otherwise. |
| STT/TTS |  | ✅ |  | ✅ | Requires optional Python deps (`openai-whisper`, `pyttsx3`). |
| Windows operator read actions |  | ✅ |  | ✅ | Read path (enumerate windows) requires daemon on Windows. |
| Windows operator write actions |  | ✅ |  | ✅ | Launch/focus/open/type implemented and approval-gated; Windows-only. |
| Browser workflows |  | ✅ |  | ✅ | Open URL + session/download paths exist; some interactive actions are typed `NOT_YET_SUPPORTED`. |
| Workspace intake and summarization |  | ✅ |  | ✅ | Mixed-type intake and summary generation implemented. |
| FRD/ZMA analysis |  | ✅ |  | ✅ | Parsers + analysis response generation implemented. |
| Crossover suggestions |  | ✅ |  | ✅ | First-pass ranking logic implemented. |
| REW workflow |  | ✅ |  | ✅ | Launch/attach/import implemented; export intentionally `not_yet_supported`. |
| Email workflow |  | ✅ |  | ✅ | Draft/review/send path implemented; requires SMTP config + secret refs. |
| Messaging workflow |  | ✅ |  | ✅ | Draft/review/send Slack-webhook path implemented; requires secret refs. |
| Artifact listing |  | ✅ |  | ✅ | Artifacts persisted and returned by `ListArtifacts`. |

## Bottom line

- All listed flows have implementation present.
- Many flows are **dependency/OS/config gated** (especially Windows operator, secure secrets, Ollama, STT/TTS, email/messaging).
- No flow in this pass is marked manually verified.
