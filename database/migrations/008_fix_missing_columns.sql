/* Migration: 008_fix_missing_columns.sql */
-- Add missing columns to tables that were already created in version 1
-- before versions 3-6 redefined them using IF NOT EXISTS (which was ignored by SQLite)

-- Update notes table
ALTER TABLE notes ADD COLUMN updated_at TEXT;

-- Update ideas table
ALTER TABLE ideas ADD COLUMN priority TEXT CHECK (priority IN ('Crítica','Alta','Média','Baixa')) DEFAULT 'Média';
ALTER TABLE ideas ADD COLUMN updated_at TEXT;

-- Update knowledge_pages table
ALTER TABLE knowledge_pages ADD COLUMN last_reviewed_at TEXT;
ALTER TABLE knowledge_pages ADD COLUMN review_interval_days INTEGER;

-- Update events table
ALTER TABLE events ADD COLUMN notes TEXT;
ALTER TABLE events ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;
ALTER TABLE events ADD COLUMN updated_at TEXT;
