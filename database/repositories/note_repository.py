from .base_repository import BaseRepository
from models.entities import Note
from database.connection import get_db_cursor

class NoteRepository(BaseRepository[Note]):
    def __init__(self):
        super().__init__('notes', Note)

    def create(self, note: Note) -> Note:
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT INTO notes (uuid, content, is_favorite, project_id, task_id, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (note.uuid, note.content, note.is_favorite, note.project_id, note.task_id))
            note.id = cursor.lastrowid
            return note

    def update(self, note: Note) -> Note:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE notes
                SET content = ?, is_favorite = ?, project_id = ?, task_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (note.content, note.is_favorite, note.project_id, note.task_id, note.id))
            return note
            
    def get_by_project_id(self, project_id: int) -> list[Note]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM notes WHERE project_id = ? AND is_archived = 0 AND deleted_at IS NULL ORDER BY created_at DESC", (project_id,))
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
