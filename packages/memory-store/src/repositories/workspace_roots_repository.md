# workspace_roots repository (scaffold)

## Purpose

Stores conversation-level workspace root attachments.

## Placeholder entity shape

- `id`
- `conversation_id`
- `display_name`
- `root_path`
- `mode` (`read_only` | `read_write`)
- `created_at`
- `updated_at`

## Interface sketch

- `get_by_id(...)`
- `list_by_conversation(...)`
- `create(...)`
- `update_mode(...)`
- `delete(...)`

Method signatures and return types are TBD.

## Notes

- This repository will be the source of truth for visible workspace roots in the chat UI.
- `workspace_files` rows will reference `workspace_roots.id` when file indexing is introduced.
