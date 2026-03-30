# workspace_files repository (scaffold)

## Purpose

Tracks discovered files under attached workspace roots.

## Placeholder entity shape

- `id`
- `workspace_root_id` (FK -> `workspace_roots.id`)
- `relative_path`
- `display_name`
- `is_directory`
- `checksum` (optional)
- `created_at`
- `updated_at`

## Interface sketch

- `get_by_id(...)`
- `list_by_workspace_root(...)`
- `create(...)`
- `update(...)`
- `delete(...)`

Method signatures and return types are TBD.

## Notes

- Initial scaffold only; no file scanning or mutation logic yet.
- Read-only vs read-write behavior will be enforced above this repository layer.
