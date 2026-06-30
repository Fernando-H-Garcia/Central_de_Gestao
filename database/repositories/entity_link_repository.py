from database.connection import get_db_cursor
from typing import List, Dict

class EntityLinkRepository:
    def add_link(self, source_type: str, source_id: int, target_type: str, target_id: int, relationship_type: str):
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT OR IGNORE INTO entity_links (source_type, source_id, target_type, target_id, relationship_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (source_type.strip(), source_id, target_type.strip(), target_id, relationship_type.strip()))

    def remove_link(self, source_type: str, source_id: int, target_type: str, target_id: int, relationship_type: str):
        with get_db_cursor() as cursor:
            cursor.execute('''
                DELETE FROM entity_links
                WHERE source_type = ? AND source_id = ? AND target_type = ? AND target_id = ? AND relationship_type = ?
            ''', (source_type.strip(), source_id, target_type.strip(), target_id, relationship_type.strip()))

    def get_links_from(self, source_type: str, source_id: int) -> List[Dict]:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT id, source_type, source_id, target_type, target_id, relationship_type, created_at
                FROM entity_links
                WHERE source_type = ? AND source_id = ?
            ''', (source_type.strip(), source_id))
            return [dict(row) for row in cursor.fetchall()]

    def get_links_to(self, target_type: str, target_id: int) -> List[Dict]:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT id, source_type, source_id, target_type, target_id, relationship_type, created_at
                FROM entity_links
                WHERE target_type = ? AND target_id = ?
            ''', (target_type.strip(), target_id))
            return [dict(row) for row in cursor.fetchall()]

    def get_links_by_type(self, source_type: str, source_id: int, relationship_type: str) -> List[Dict]:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT id, source_type, source_id, target_type, target_id, relationship_type, created_at
                FROM entity_links
                WHERE source_type = ? AND source_id = ? AND relationship_type = ?
            ''', (source_type.strip(), source_id, relationship_type.strip()))
            return [dict(row) for row in cursor.fetchall()]
