/* Migration: 004_notes_schema.sql */
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    is_favorite INTEGER DEFAULT 0,
    last_accessed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    is_archived INTEGER DEFAULT 0,
    archived_at TEXT,
    deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_notes_uuid ON notes(uuid);
CREATE INDEX IF NOT EXISTS idx_notes_is_archived ON notes(is_archived);
