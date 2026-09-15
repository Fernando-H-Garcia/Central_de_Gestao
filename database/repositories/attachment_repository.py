from typing import List
from database.connection import get_db_cursor
from models.entities import Attachment

class AttachmentRepository:
    def __init__(self):
        self.table_name = "attachments"

    def _row_to_model(self, row) -> Attachment:
        if not row:
            return None
        return Attachment(**dict(row))

    def get_by_entity(self, entity_type: str, entity_id: int) -> List[Attachment]:
        with get_db_cursor() as cursor:
            cursor.execute(f"""
                SELECT * FROM {self.table_name} 
                WHERE entity_type = ? AND entity_id = ? AND deleted_at IS NULL
                ORDER BY created_at DESC
            """, (entity_type, entity_id))
            return [self._row_to_model(row) for row in cursor.fetchall()]

    def create(self, attachment: Attachment) -> Attachment:
        with get_db_cursor() as cursor:
            cursor.execute(f"""
                INSERT INTO {self.table_name} 
                (uuid, entity_type, entity_id, file_path, file_name, mime_type, file_size, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attachment.uuid, attachment.entity_type, attachment.entity_id,
                attachment.file_path, attachment.file_name, attachment.mime_type,
                attachment.file_size, attachment.checksum
            ))
            attachment.id = cursor.lastrowid
            return attachment

    def soft_delete(self, id: int):
        with get_db_cursor() as cursor:
            cursor.execute(f"UPDATE {self.table_name} SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))

    def get_by_id(self, id: int) -> Attachment:
        with get_db_cursor() as cursor:
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (id,))
            return self._row_to_model(cursor.fetchone())

    def update(self, attachment: Attachment) -> Attachment:
        with get_db_cursor() as cursor:
            cursor.execute(f"""
                UPDATE {self.table_name}
                SET entity_type = ?, entity_id = ?, file_name = ?, file_path = ?, mime_type = ?
                WHERE id = ?
            """, (attachment.entity_type, attachment.entity_id, attachment.file_name, attachment.file_path, attachment.mime_type, attachment.id))
            return attachment

    def rename(self, attachment_id: int, new_file_name: str) -> Attachment:
        with get_db_cursor() as cursor:
            cursor.execute(f"UPDATE {self.table_name} SET file_name = ? WHERE id = ?", (new_file_name, attachment_id))
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (attachment_id,))
            return self._row_to_model(cursor.fetchone())
