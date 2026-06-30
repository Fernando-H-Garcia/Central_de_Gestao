-- Etapa 1 da Fase 2: Performance Indexes para curar o Full Table Scan do SQLite

-- TASKS
CREATE INDEX IF NOT EXISTS idx_tasks_archived_deleted ON tasks(is_archived, deleted_at);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_parent_id ON tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- PROJECTS
CREATE INDEX IF NOT EXISTS idx_projects_archived_deleted ON projects(is_archived, deleted_at);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

-- IDEAS
CREATE INDEX IF NOT EXISTS idx_ideas_project_id ON ideas(project_id);
CREATE INDEX IF NOT EXISTS idx_ideas_task_id ON ideas(task_id);

-- NOTES
CREATE INDEX IF NOT EXISTS idx_notes_task_id ON notes(task_id);

-- ACTIVITY LOGS
CREATE INDEX IF NOT EXISTS idx_activity_logs_entity ON activity_logs(entity_type, entity_id);
