CREATE TABLE IF NOT EXISTS workspace_roots (
    root_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    root_path TEXT NOT NULL,
    display_name TEXT NOT NULL,
    access_mode TEXT NOT NULL,
    file_count INTEGER NOT NULL DEFAULT 0,
    attached_at TEXT NOT NULL,
    last_scanned_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    UNIQUE (conversation_id, root_path)
);

CREATE TABLE IF NOT EXISTS workspace_files (
    file_id TEXT PRIMARY KEY,
    root_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    discovered_at TEXT NOT NULL,
    FOREIGN KEY (root_id) REFERENCES workspace_roots(root_id) ON DELETE CASCADE,
    UNIQUE (root_id, relative_path)
);

CREATE INDEX IF NOT EXISTS idx_workspace_roots_conversation ON workspace_roots(conversation_id, attached_at DESC);
CREATE INDEX IF NOT EXISTS idx_workspace_files_root ON workspace_files(root_id, relative_path ASC);
