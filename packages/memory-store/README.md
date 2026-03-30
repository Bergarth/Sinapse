# memory-store

SQLite storage scaffold for shared memory and task-tracking data.

## Status

Scaffold only. No runtime implementation is included yet.

## Planned tables

- `app_settings`
- `conversations`
- `messages`
- `tasks`
- `task_steps`
- `approvals`
- `artifacts`
- `routines`
- `permissions`
- `workspace_roots`
- `workspace_files`

## Package layout

- `migrations/` - placeholder migration files for SQLite schema changes
- `docs/schema/` - table-by-table schema planning notes
- `src/repositories/` - repository interface placeholders only

## Notes for contractors

- Keep this package dependency-light.
- Add schema changes through numbered SQL migrations.
- Keep interfaces stable before adding adapters or business logic.
