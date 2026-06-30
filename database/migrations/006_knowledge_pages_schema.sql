/* Migration: 006_knowledge_pages_schema.sql */
CREATE TABLE IF NOT EXISTS knowledge_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT,
    parent_id INTEGER,
    category TEXT,
    is_favorite INTEGER DEFAULT 0,
    last_reviewed_at TEXT,
    review_interval_days INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    is_archived INTEGER DEFAULT 0,
    archived_at TEXT,
    deleted_at TEXT,
    CONSTRAINT fk_kp_parent FOREIGN KEY (parent_id) REFERENCES knowledge_pages(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_kp_uuid ON knowledge_pages(uuid);
CREATE INDEX IF NOT EXISTS idx_kp_parent ON knowledge_pages(parent_id);
