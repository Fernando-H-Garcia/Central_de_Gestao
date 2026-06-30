from database.connection import get_db_cursor
from typing import List, Optional, TypeVar, Generic, Type

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, table_name: str, model_class: Type[T]):
        self.table_name = table_name
        self.model_class = model_class

    def _row_to_model(self, row) -> T:
        if not row:
            return None
        return self.model_class(**dict(row))

    def get_by_id(self, id: int) -> Optional[T]:
        with get_db_cursor() as cursor:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (id,))
            row = cursor.fetchone()
            return self._row_to_model(row)

    def get_by_uuid(self, uuid: str) -> Optional[T]:
        with get_db_cursor() as cursor:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE uuid = ?", (uuid,))
            row = cursor.fetchone()
            return self._row_to_model(row)

    def get_all(self, include_archived=False, include_deleted=False) -> List[T]:
        query = f"SELECT * FROM {self.table_name} WHERE 1=1"
        if not include_archived:
            query += " AND is_archived = 0"
        if not include_deleted:
            query += " AND deleted_at IS NULL"
            
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [self._row_to_model(row) for row in cursor.fetchall()]

    def delete(self, id: int):
        """Hard delete (not recommended for most entities)."""
        with get_db_cursor() as cursor:
            cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (id,))

    def soft_delete(self, id: int):
        with get_db_cursor() as cursor:
            cursor.execute(f"UPDATE {self.table_name} SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))

    def archive(self, id: int):
        with get_db_cursor() as cursor:
            cursor.execute(f"UPDATE {self.table_name} SET is_archived = 1, archived_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))

    def restore(self, id: int):
        with get_db_cursor() as cursor:
            cursor.execute(f"UPDATE {self.table_name} SET is_archived = 0, archived_at = NULL, deleted_at = NULL WHERE id = ?", (id,))
