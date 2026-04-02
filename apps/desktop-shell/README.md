# desktop-shell

WinUI 3 desktop shell for Sinapse.

> This shell is **not just scaffold** anymore: it is wired to the daemon over shared gRPC contracts.

## What it does today

- Connects to daemon endpoint (default `http://127.0.0.1:50051`) and shows health/capability status.
- Shows first-run dependency checks from daemon startup status (daemon/Ollama/windows-operator/secure-secrets/STT/TTS/email/messaging readiness).
- Sends chat messages and renders persisted conversation history.
- Attaches workspace folders and shows scanned root summaries.
- Loads and saves daemon app settings (model/search/speech/provider entries).
- Starts tasks and listens to live timeline events from `ObserveSystemState`.
- Shows approval prompts and can approve/deny/cancel from the UI.
- Supports push-to-talk recording and daemon STT requests.
- Supports spoken assistant replies via daemon TTS + local WAV playback.

## Current limitations

- This repo pass did not manually verify all shell flows end-to-end.
- Availability of STT/TTS depends on daemon-side optional dependencies.
- Some settings and communications paths are dependency-gated and may remain unavailable until Windows-hosted secure storage + secrets are configured.
- Some daemon task paths intentionally return `NOT_YET_SUPPORTED` for unsupported automation (for example certain browser interactive actions).

## Build notes

- Project file: `src/DesktopShell/DesktopShell.csproj`
- Contracts are sourced from: `packages/contracts/src/sinapse/contracts/v1/contracts.proto`
- The shell expects a running daemon implementing `DaemonContract`.
