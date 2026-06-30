from database.connection import get_db_cursor
from models.base import BaseModel
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ActivityLog(BaseModel):
    entity_type: str = ""
    entity_id: int = 0
    action: str = ""
    changed_fields_json: Optional[str] = None

class ActivityLogRepository:
    def create(self, log: ActivityLog):
        from datetime import datetime
        local_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO activity_logs (entity_type, entity_id, action, changed_fields_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (log.entity_type, log.entity_id, log.action, log.changed_fields_json, local_now))

    def get_by_entity(self, entity_type: str, entity_id: int) -> List[ActivityLog]:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT id, entity_type, entity_id, action, changed_fields_json, created_at
                FROM activity_logs
                WHERE entity_type = ? AND entity_id = ?
                ORDER BY created_at DESC
            """, (entity_type, entity_id))
            
            logs = []
            for row in cursor.fetchall():
                log = ActivityLog(
                    entity_type=row['entity_type'],
                    entity_id=row['entity_id'],
                    action=row['action'],
                    changed_fields_json=row['changed_fields_json']
                )
                log.id = row['id']
                log.created_at = row['created_at']
                logs.append(log)
            return logs

    def update_changed_fields(self, log_id: int, changed_fields_json: str):
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE activity_logs
                SET changed_fields_json = ?
                WHERE id = ?
            """, (changed_fields_json, log_id))

    def delete(self, log_id: int):
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM activity_logs WHERE id = ?", (log_id,))
