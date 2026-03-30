# repository interfaces

Interface placeholders for data access boundaries.

No concrete adapters or SQL execution logic is implemented yet.

## Workspace attachment placeholders

- `workspace_roots_repository`: conversation-to-root attachment records, including mode (`read_only`/`read_write`).
- `workspace_files_repository`: file references underneath a workspace root.

These are scaffold references only for now and intentionally exclude real filesystem modification logic.
