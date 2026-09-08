-- Migration 026: Repetir alarme a cada X dias Y vezes
ALTER TABLE alerts ADD COLUMN recurrence_interval INTEGER;
ALTER TABLE alerts ADD COLUMN recurrence_count INTEGER;
ALTER TABLE alerts ADD COLUMN recurrence_group_id TEXT;
CREATE INDEX IF NOT EXISTS idx_alerts_group ON alerts(recurrence_group_id);
