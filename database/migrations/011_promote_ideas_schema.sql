/* Migration: 011_promote_ideas_schema.sql */

-- Add promotion linkage fields to ideas
ALTER TABLE ideas ADD COLUMN linked_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE ideas ADD COLUMN linked_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL;
ALTER TABLE ideas ADD COLUMN promoted_at DATETIME;
ALTER TABLE ideas ADD COLUMN promoted_type TEXT;

-- Add originating fields to projects and tasks
ALTER TABLE projects ADD COLUMN originated_from_idea_id INTEGER REFERENCES ideas(id) ON DELETE SET NULL;
ALTER TABLE tasks ADD COLUMN originated_from_idea_id INTEGER REFERENCES ideas(id) ON DELETE SET NULL;

-- Create tagging tables for ideas, projects, and tasks
CREATE TABLE IF NOT EXISTS idea_tags (
    idea_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (idea_id, tag_id),
    FOREIGN KEY (idea_id) REFERENCES ideas(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_tags (
    project_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (project_id, tag_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS task_tags (
    task_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (task_id, tag_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
