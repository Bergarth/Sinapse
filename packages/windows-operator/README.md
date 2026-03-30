# windows-operator

Windows desktop operator package with a safety-scoped first write phase.

Implemented actions:
- `enumerate_open_windows()` (read-only)
- `launch_application(app_name | executable_path)`
- `focus_window(window_ref)` (title/class hint)
- `open_file(file_path)` (local files only)
- `type_text(target, text)` (focused target or focus-by-title then type)

Safety boundaries:
- No destructive actions (delete/remove/format/admin mutation).
- No raw shell command execution endpoint.
- The daemon is responsible for approval-gating mutating actions before calling these methods.
