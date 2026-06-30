/* Migration: 012_entity_links_schema.sql */

CREATE TABLE IF NOT EXISTS entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,       -- 'idea', 'project', 'task', 'note'
    source_id INTEGER NOT NULL,
    target_type TEXT NOT NULL,       -- 'idea', 'project', 'task', 'note'
    target_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,  -- 'promoted_to', 'originated_from', 'derived', etc.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_type, source_id, target_type, target_id, relationship_type)
);

-- Migrate existing linked projects from ideas
INSERT OR IGNORE INTO entity_links (source_type, source_id, target_type, target_id, relationship_type)
SELECT 'idea', id, 'project', linked_project_id, 'promoted_to'
FROM ideas WHERE linked_project_id IS NOT NULL;

-- Migrate existing linked tasks from ideas
INSERT OR IGNORE INTO entity_links (source_type, source_id, target_type, target_id, relationship_type)
SELECT 'idea', id, 'task', linked_task_id, 'promoted_to'
FROM ideas WHERE linked_task_id IS NOT NULL;

-- Migrate existing originated_from_idea_id from projects
INSERT OR IGNORE INTO entity_links (source_type, source_id, target_type, target_id, relationship_type)
SELECT 'project', id, 'idea', originated_from_idea_id, 'originated_from'
FROM projects WHERE originated_from_idea_id IS NOT NULL;

-- Migrate existing originated_from_idea_id from tasks
INSERT OR IGNORE INTO entity_links (source_type, source_id, target_type, target_id, relationship_type)
SELECT 'task', id, 'idea', originated_from_idea_id, 'originated_from'
FROM tasks WHERE originated_from_idea_id IS NOT NULL;
