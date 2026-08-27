from .base_repository import BaseRepository
from models.entities import TaskDeadline
from database.connection import get_db_cursor
from datetime import datetime, date


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


class TaskDeadlineRepository(BaseRepository[TaskDeadline]):
    def __init__(self):
        super().__init__("task_deadlines", TaskDeadline)

    def _row_to_model(self, row):
        model = super()._row_to_model(row)
        if model is not None:
            model.deadline_date = _parse_date(model.deadline_date)
        return model

    def get_by_task(self, task_id: int) -> list:
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM task_deadlines WHERE task_id = ? AND deleted_at IS NULL ORDER BY deadline_date",
                (task_id,),
            )
            return [self._row_to_model(r) for r in cursor.fetchall()]

    def create(self, task_id: int, deadline_date, description=None,
               alarm_week_id=None, alarm_day_id=None) -> TaskDeadline:
        from models.base import generate_uuid
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO task_deadlines (uuid, task_id, deadline_date, description, alarm_week_id, alarm_day_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (generate_uuid(), task_id, deadline_date, description, alarm_week_id, alarm_day_id),
            )
            new_id = cursor.lastrowid
        return self.get_by_id(new_id)

    def update(self, deadline: TaskDeadline) -> TaskDeadline:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE task_deadlines
                SET task_id = ?, deadline_date = ?, description = ?, alarm_week_id = ?, alarm_day_id = ?
                WHERE id = ?
                """,
                (deadline.task_id, deadline.deadline_date, deadline.description,
                 deadline.alarm_week_id, deadline.alarm_day_id, deadline.id),
            )
        return deadline

    def soft_delete(self, deadline_id: int):
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE task_deadlines SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
                (deadline_id,),
            )
