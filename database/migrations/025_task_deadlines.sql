CREATE TABLE task_deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT,
    task_id INTEGER NOT NULL,
    deadline_date DATE,
    description TEXT,
    alarm_week_id INTEGER,
    alarm_day_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Migra os prazos estimados únicos existentes (tasks.estimated_deadline) para a
-- nova tabela, preservando as descrições e os ids dos alarmes automáticos.
INSERT INTO task_deadlines (task_id, deadline_date, description, alarm_week_id, alarm_day_id)
SELECT id, estimated_deadline, estimated_deadline_desc, deadline_alarm_week, deadline_alarm_day
FROM tasks
WHERE estimated_deadline IS NOT NULL;
