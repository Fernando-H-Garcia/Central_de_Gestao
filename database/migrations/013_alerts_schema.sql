/* Migration: 013_alerts_schema.sql */

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,       -- 'project', 'task', 'idea', 'wiki'
    entity_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    alert_date TEXT NOT NULL,        -- 'YYYY-MM-DD'
    alert_time TEXT,                 -- 'HH:MM'
    priority TEXT DEFAULT 'medium',  -- 'high' (red), 'medium' (yellow), 'low' (blue)
    status TEXT DEFAULT 'pending',   -- 'pending', 'completed', 'dismissed', 'cancelled'
    recurrence_type TEXT DEFAULT 'none', -- 'none', 'daily', 'weekly', 'monthly', 'yearly'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alerts_entity ON alerts(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_alerts_date ON alerts(alert_date);

-- One-time migration from tasks
INSERT INTO alerts (entity_type, entity_id, title, alert_date, priority, status)
SELECT 'task', id, COALESCE(NULLIF(alert_message, ''), 'Lembrete da tarefa'), alert_date, 'medium', 'pending'
FROM tasks 
WHERE alert_date IS NOT NULL AND alert_date != '';

-- One-time migration from projects
INSERT INTO alerts (entity_type, entity_id, title, alert_date, priority, status)
SELECT 'project', id, COALESCE(NULLIF(alert_message, ''), 'Lembrete do projeto'), alert_date, 'medium', 'pending'
FROM projects 
WHERE alert_date IS NOT NULL AND alert_date != '';
