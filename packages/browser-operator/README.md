# browser-operator

Safe browser-operator package used by the daemon.

## Currently supported

- Read-only URL open with visible-content summary.
- Controlled browser-session bootstrap (`open_browser_session`) that creates a profile root and session state record.
- Explicit session-style actions:
  - navigate to URL (`navigate`)
  - read visible content (`read_visible_content`)
  - download a file into workspace path (`download`)
  - upload from workspace path (`upload`) with explicit typed `NOT_YET_SUPPORTED` when generic DOM file-input automation is unavailable.

## Safety behavior

- Interactive actions stay explicit; nothing auto-clicks or auto-fills in the background.
- Unsupported actions return typed `NOT_YET_SUPPORTED:*` details instead of fake success.
- Read-only open/summarize path works without Playwright.
