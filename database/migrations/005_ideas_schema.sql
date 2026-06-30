/* Migration: 005_ideas_schema.sql */
CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    project_id INTEGER,
    category TEXT,
    interest_level INTEGER DEFAULT 3,
    status TEXT DEFAULT 'Nova',
    priority TEXT CHECK (priority IN ('Crítica','Alta','Média','Baixa')) DEFAULT 'Média',
    is_favorite INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT,
    is_archived INTEGER DEFAULT 0,
    archived_at TEXT,
    deleted_at TEXT,
    CONSTRAINT fk_ideas_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ideas_uuid ON ideas(uuid);
CREATE INDEX IF NOT EXISTS idx_ideas_is_archived ON ideas(is_archived);
