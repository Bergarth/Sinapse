# approvals

Tracks runtime approval requests and decisions for risky task steps.

## Columns

- `approval_id` (TEXT, PK)
- `task_id` (TEXT, FK -> `tasks.task_id`)
- `step_id` (TEXT, FK -> `task_steps.step_id`)
- `risk_class` (TEXT: `read`, `write`, `send`, `destructive`)
- `action_title` (TEXT)
- `action_target` (TEXT)
- `reason` (TEXT)
- `status` (TEXT: `pending`, `approved`, `rejected`)
- `requested_by` (TEXT)
- `decided_by` (TEXT)
- `note` (TEXT)
- `requested_at` (TEXT, ISO timestamp)
- `decided_at` (TEXT, ISO timestamp)

## Indexes

- `idx_approvals_task_requested_at` for task-level audit queries.
- `idx_approvals_step_status` for step lookup and pending decision checks.
