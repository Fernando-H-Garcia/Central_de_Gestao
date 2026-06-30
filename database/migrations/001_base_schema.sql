PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- V1 Schema starts at version 1
INSERT OR IGNORE INTO schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Default settings
INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'System');
INSERT OR IGNORE INTO settings (key, value) VALUES ('sidebar_width', '200');
INSERT OR IGNORE INTO settings (key, value) VALUES ('autosave_interval_sec', '30');
INSERT OR IGNORE INTO settings (key, value) VALUES ('max_backups', '30');
INSERT OR IGNORE INTO settings (key, value) VALUES ('export_dir', '');
INSERT OR IGNORE INTO settings (key, value) VALUES ('attachments_dir', 'attachments');
INSERT OR IGNORE INTO settings (key, value) VALUES ('default_screen', 'Workbench');

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER,
    checksum TEXT,
    deleted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    objective TEXT,
    priority TEXT DEFAULT 'Média',
    health_status TEXT DEFAULT 'Verde',
    status TEXT NOT NULL DEFAULT 'Ativo',
    blocked_reason TEXT,
    blocked_since DATETIME,
    is_favorite BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    archived_at DATETIME,
    deleted_at DATETIME,
    last_accessed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    parent_task_id INTEGER NULL,
    project_id INTEGER NULL,
    title TEXT NOT NULL,
    context TEXT,
    energy_level TEXT DEFAULT 'Média',
    status TEXT DEFAULT 'Backlog',
    position REAL,
    is_favorite BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    archived_at DATETIME,
    deleted_at DATETIME,
    last_accessed_at DATETIME,
    due_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY(parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME,
    location TEXT,
    is_archived BOOLEAN DEFAULT 0,
    archived_at DATETIME,
    deleted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    project_id INTEGER NULL,
    task_id INTEGER NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    interest_level INTEGER DEFAULT 3,
    status TEXT DEFAULT 'Nova',
    is_favorite BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    archived_at DATETIME,
    deleted_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    is_favorite BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    archived_at DATETIME,
    deleted_at DATETIME,
    last_accessed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    task_id INTEGER NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS knowledge_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    parent_id INTEGER NULL,
    title TEXT NOT NULL,
    content TEXT,
    category TEXT,
    is_favorite BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    archived_at DATETIME,
    deleted_at DATETIME,
    last_accessed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY(parent_id) REFERENCES knowledge_pages(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    changed_fields_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS global_search USING fts5(
    entity_type,
    entity_id,
    title,
    content
);

-- Triggers para preenchimento automático do FTS5
-- Tarefas
CREATE TRIGGER IF NOT EXISTS t_tasks_ai AFTER INSERT ON tasks BEGIN
  INSERT INTO global_search(entity_type, entity_id, title, content) 
  VALUES ('task', new.id, new.title, new.context);
END;

CREATE TRIGGER IF NOT EXISTS t_tasks_au AFTER UPDATE ON tasks BEGIN
  UPDATE global_search SET title = new.title, content = new.context
  WHERE entity_type = 'task' AND entity_id = new.id;
END;

CREATE TRIGGER IF NOT EXISTS t_tasks_ad AFTER DELETE ON tasks BEGIN
  DELETE FROM global_search WHERE entity_type = 'task' AND entity_id = old.id;
END;

-- Projetos
CREATE TRIGGER IF NOT EXISTS t_projects_ai AFTER INSERT ON projects BEGIN
  INSERT INTO global_search(entity_type, entity_id, title, content) 
  VALUES ('project', new.id, new.name, new.objective);
END;

CREATE TRIGGER IF NOT EXISTS t_projects_au AFTER UPDATE ON projects BEGIN
  UPDATE global_search SET title = new.name, content = new.objective
  WHERE entity_type = 'project' AND entity_id = new.id;
END;

CREATE TRIGGER IF NOT EXISTS t_projects_ad AFTER DELETE ON projects BEGIN
  DELETE FROM global_search WHERE entity_type = 'project' AND entity_id = old.id;
END;

-- Ideas
CREATE TRIGGER IF NOT EXISTS t_ideas_ai AFTER INSERT ON ideas BEGIN
  INSERT INTO global_search(entity_type, entity_id, title, content) 
  VALUES ('idea', new.id, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS t_ideas_au AFTER UPDATE ON ideas BEGIN
  UPDATE global_search SET title = new.title, content = new.description
  WHERE entity_type = 'idea' AND entity_id = new.id;
END;

CREATE TRIGGER IF NOT EXISTS t_ideas_ad AFTER DELETE ON ideas BEGIN
  DELETE FROM global_search WHERE entity_type = 'idea' AND entity_id = old.id;
END;

-- Notes
CREATE TRIGGER IF NOT EXISTS t_notes_ai AFTER INSERT ON notes BEGIN
  INSERT INTO global_search(entity_type, entity_id, title, content) 
  VALUES ('note', new.id, substr(new.content, 1, 50), new.content);
END;

CREATE TRIGGER IF NOT EXISTS t_notes_au AFTER UPDATE ON notes BEGIN
  UPDATE global_search SET title = substr(new.content, 1, 50), content = new.content
  WHERE entity_type = 'note' AND entity_id = new.id;
END;

CREATE TRIGGER IF NOT EXISTS t_notes_ad AFTER DELETE ON notes BEGIN
  DELETE FROM global_search WHERE entity_type = 'note' AND entity_id = old.id;
END;

-- Knowledge Pages
CREATE TRIGGER IF NOT EXISTS t_kp_ai AFTER INSERT ON knowledge_pages BEGIN
  INSERT INTO global_search(entity_type, entity_id, title, content) 
  VALUES ('knowledge_page', new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS t_kp_au AFTER UPDATE ON knowledge_pages BEGIN
  UPDATE global_search SET title = new.title, content = new.content
  WHERE entity_type = 'knowledge_page' AND entity_id = new.id;
END;

CREATE TRIGGER IF NOT EXISTS t_kp_ad AFTER DELETE ON knowledge_pages BEGIN
  DELETE FROM global_search WHERE entity_type = 'knowledge_page' AND entity_id = old.id;
END;

-- Events
CREATE TRIGGER IF NOT EXISTS t_events_ai AFTER INSERT ON events BEGIN
  INSERT INTO global_search(entity_type, entity_id, title, content) 
  VALUES ('event', new.id, new.title, new.description || ' ' || COALESCE(new.location, ''));
END;

CREATE TRIGGER IF NOT EXISTS t_events_au AFTER UPDATE ON events BEGIN
  UPDATE global_search SET title = new.title, content = new.description || ' ' || COALESCE(new.location, '')
  WHERE entity_type = 'event' AND entity_id = new.id;
END;

CREATE TRIGGER IF NOT EXISTS t_events_ad AFTER DELETE ON events BEGIN
  DELETE FROM global_search WHERE entity_type = 'event' AND entity_id = old.id;
END;
