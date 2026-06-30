from database.repositories.base_repository import BaseRepository
from models.alert import Alert
from database.connection import get_db_cursor

class AlertRepository(BaseRepository[Alert]):
    def __init__(self):
        super().__init__('alerts', Alert)

    def create(self, alert: Alert) -> Alert:
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT INTO alerts (entity_type, entity_id, title, description, alert_date, alert_time, priority, status, recurrence_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (alert.entity_type, alert.entity_id, alert.title, alert.description, alert.alert_date, alert.alert_time, alert.priority, alert.status, alert.recurrence_type))
            alert.id = cursor.lastrowid
            return alert

    def update(self, alert: Alert) -> Alert:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE alerts
                SET title = ?, description = ?, alert_date = ?, alert_time = ?, priority = ?, status = ?, recurrence_type = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (alert.title, alert.description, alert.alert_date, alert.alert_time, alert.priority, alert.status, alert.recurrence_type, alert.id))
            return alert

    def get_all(self, include_archived=False, include_deleted=False) -> list:
        # Overriding to avoid SQL errors since alerts table doesn't have deleted_at or is_archived columns
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM alerts")
            return [self._row_to_model(row) for row in cursor.fetchall()]

    def mark_overdue(self, current_date: str, current_time: str):
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE alerts
                SET status = 'overdue', updated_at = datetime('now')
                WHERE status = 'pending'
                  AND (
                    alert_date < ?
                    OR (alert_date = ? AND alert_time IS NOT NULL AND alert_time != '' AND alert_time <= ?)
                  )
            ''', (current_date, current_date, current_time))

