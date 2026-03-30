CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    risk_class TEXT NOT NULL,
    action_title TEXT NOT NULL,
    action_target TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    decided_by TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    requested_at TEXT NOT NULL,
    decided_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES task_steps(step_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_approvals_task_requested_at ON approvals(task_id, requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_approvals_step_status ON approvals(step_id, status);
