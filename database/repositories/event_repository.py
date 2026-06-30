from .base_repository import BaseRepository
from models.entities import Event
from database.connection import get_db_cursor

class EventRepository(BaseRepository[Event]):
    def __init__(self):
        super().__init__("events", Event)

    def create(self, event: Event) -> Event:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO events (uuid, title, description, start_datetime, end_datetime, location, notes, project_id, task_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event.uuid, event.title, event.description, event.start_datetime, event.end_datetime, event.location, event.notes, event.project_id, event.task_id),
            )
            event.id = cursor.lastrowid
            return event

    def update(self, event: Event) -> Event:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE events
                SET title = ?, description = ?, start_datetime = ?, end_datetime = ?, location = ?, notes = ?, project_id = ?, task_id = ?, is_archived = ?, deleted_at = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    event.title,
                    event.description,
                    event.start_datetime,
                    event.end_datetime,
                    event.location,
                    event.notes,
                    event.project_id,
                    event.task_id,
                    event.is_archived,
                    event.deleted_at,
                    event.id,
                ),
            )
            return event
