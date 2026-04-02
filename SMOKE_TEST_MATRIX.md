# SMOKE_TEST_MATRIX

Date: 2026-04-02

This matrix is a **truth pass from code + dependency gates**, not a full manual QA execution on a Windows machine.

Definitions used:
- **Implemented**: flow is present in code.
- **Runnable with config/dependencies**: flow should run when required OS/dependencies/config exist.
- **Manually verified**: executed end-to-end by a human in this pass.
- **Intentionally not yet supported**: known explicit product gap (not a bug).

| User-visible flow | Implemented | Runnable with config/dependencies | Manually verified | Intentionally not yet supported | Notes |
|---|---|---|---|---|---|
| Shell ↔ daemon connection | ✅ | ✅ | ❌ | ❌ | Startup health/status path is wired and reports dependency gates. |
| Chat and persistence | ✅ | ✅ | ❌ | ❌ | Placeholder fallback keeps chat usable if Ollama is unavailable. |
| Settings and secure secret references | ✅ | ✅ | ❌ | ❌ | Secure writes/readiness are Windows-daemon gated. |
| Approvals and restart recovery | ✅ | ✅ | ❌ | ❌ | Pending approvals restore on startup. |
| Ollama local-model path | ✅ | ✅ | ❌ | ❌ | Requires running Ollama service. |
| STT | ✅ | ✅ | ❌ | ❌ | Requires optional `openai-whisper`. |
| TTS | ✅ | ✅ | ❌ | ❌ | Requires optional `pyttsx3`. |
| Windows operator read actions | ✅ | ✅ | ❌ | ❌ | Windows-only runtime capability. |
| Windows operator write actions | ✅ | ✅ | ❌ | ❌ | Approval-gated; Windows-only runtime capability. |
| Browser workflows (supported subset) | ✅ | ✅ | ❌ | ❌ | Open URL + controlled workflow envelope implemented. |
| Browser interactive unsupported subset | ✅ | ❌ | ❌ | ✅ | Unsupported actions explicitly return `NOT_YET_SUPPORTED`. |
| Workspace intake and summarization | ✅ | ✅ | ❌ | ❌ | Mixed-type intake/summarization path implemented. |
| FRD/ZMA analysis | ✅ | ✅ | ❌ | ❌ | Parsers + summary response generation implemented. |
| Crossover suggestions | ✅ | ✅ | ❌ | ❌ | First-pass ranking logic implemented. |
| REW launch/attach/import | ✅ | ✅ | ❌ | ❌ | Implemented via Windows operator-assisted integration. |
| REW export | ✅ | ❌ | ❌ | ✅ | Explicitly out of scope for this RC. |
| Email workflow | ✅ | ✅ | ❌ | ❌ | Requires SMTP config + `secret://local/...` reference readiness. |
| Messaging workflow (Slack webhook) | ✅ | ✅ | ❌ | ❌ | Requires Slack webhook secret reference readiness. |
| Messaging providers beyond Slack webhook | ✅ | ❌ | ❌ | ✅ | Non-Slack providers return `NOT_YET_SUPPORTED`. |
| Artifact listing | ✅ | ✅ | ❌ | ❌ | Artifacts persisted and returned by `ListArtifacts`. |

## Bottom line

- Implementation coverage is broad.
- Practical usage is dependency-gated in a few key areas (Windows host, secrets, Ollama, STT/TTS, communications config).
- Manual verification still needs to be completed on a real Windows PC using `docs/WINDOWS_SMOKE_TEST_CHECKLIST.md`.
