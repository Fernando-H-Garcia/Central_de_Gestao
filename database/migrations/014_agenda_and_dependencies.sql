-- Migration: 014_agenda_and_dependencies
-- Description: Creates tables for global scheduling agenda items, user daily capacity, and task dependencies.

CREATE TABLE IF NOT EXISTS agenda_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,                  -- 'task', 'project', 'idea', etc.
    entity_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,                   -- YYYY-MM-DD
    end_date TEXT NOT NULL,                     -- YYYY-MM-DD
    effort_hours REAL DEFAULT 0.0,
    schedule_status TEXT DEFAULT 'planejado',   -- 'planejado', 'em_andamento', 'pausado', 'cancelado', 'concluido'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agenda_entity ON agenda_items(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_agenda_dates ON agenda_items(start_date, end_date);

CREATE TABLE IF NOT EXISTS task_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    depends_on_task_id INTEGER NOT NULL,
    dependency_type TEXT DEFAULT 'finish_to_start', -- 'finish_to_start', 'start_to_start', 'finish_to_finish', 'blocks', 'related'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_task_dep_task ON task_dependencies(task_id);
CREATE INDEX IF NOT EXISTS idx_task_dep_depends ON task_dependencies(depends_on_task_id);

CREATE TABLE IF NOT EXISTS user_capacity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,                  -- YYYY-MM-DD
    available_hours REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
