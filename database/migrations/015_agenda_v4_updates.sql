-- Migration 015: Agenda v4 Updates (Hours, Milestones, Dependency Strength)
ALTER TABLE tasks ADD COLUMN estimated_hours REAL DEFAULT 0.0;
ALTER TABLE tasks ADD COLUMN is_milestone BOOLEAN DEFAULT 0;
ALTER TABLE task_dependencies ADD COLUMN dependency_strength TEXT DEFAULT 'obrigatória';
