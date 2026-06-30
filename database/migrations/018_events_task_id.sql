/* Migration: 018_events_task_id.sql */
ALTER TABLE events ADD COLUMN task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL;
