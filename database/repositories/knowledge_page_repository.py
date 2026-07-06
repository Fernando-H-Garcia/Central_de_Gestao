from .base_repository import BaseRepository
from models.entities import KnowledgePage
from database.connection import get_db_cursor

class KnowledgePageRepository(BaseRepository[KnowledgePage]):
    def __init__(self):
        super().__init__('knowledge_pages', KnowledgePage)

    def get_all(self, include_archived=False, include_deleted=False) -> list:
        query = f"SELECT * FROM {self.table_name} WHERE 1=1"
        if not include_archived:
            query += " AND is_archived = 0"
        if not include_deleted:
            query += " AND deleted_at IS NULL"
        query += " ORDER BY sort_order, id"
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [self._row_to_model(row) for row in cursor.fetchall()]

    def create(self, page: KnowledgePage) -> KnowledgePage:
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT INTO knowledge_pages (uuid, title, content, parent_id, category, is_favorite, sort_order, last_reviewed_at, review_interval_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (page.uuid, page.title, page.content, page.parent_id, page.category, page.is_favorite, page.sort_order, page.last_reviewed_at, page.review_interval_days))
            page.id = cursor.lastrowid
            return page

    def update(self, page: KnowledgePage) -> KnowledgePage:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE knowledge_pages
                SET title = ?, content = ?, parent_id = ?, category = ?, is_favorite = ?, sort_order = ?, last_reviewed_at = ?, review_interval_days = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (page.title, page.content, page.parent_id, page.category, page.is_favorite, page.sort_order, page.last_reviewed_at, page.review_interval_days, page.id))
            return page

    def update_sort_order(self, page_id: int, sort_order: int, parent_id: int = None):
        with get_db_cursor() as cursor:
            if parent_id is not None:
                cursor.execute("UPDATE knowledge_pages SET sort_order = ?, parent_id = ?, updated_at = datetime('now') WHERE id = ?", (sort_order, parent_id, page_id))
            else:
                cursor.execute("UPDATE knowledge_pages SET sort_order = ?, updated_at = datetime('now') WHERE id = ?", (sort_order, page_id))

    def get_tags_for_page(self, page_id: int) -> list:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT t.name FROM tags t
                JOIN knowledge_page_tags kpt ON t.id = kpt.tag_id
                WHERE kpt.knowledge_page_id = ?
            ''', (page_id,))
            return [row[0] for row in cursor.fetchall()]

    def set_tags_for_page(self, page_id: int, tags: list):
        with get_db_cursor() as cursor:
            cursor.execute('DELETE FROM knowledge_page_tags WHERE knowledge_page_id = ?', (page_id,))
            for tag in tags:
                tag_name = tag.strip()
                if not tag_name:
                    continue
                cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                row = cursor.fetchone()
                if row:
                    tag_id = row[0]
                    cursor.execute('INSERT OR IGNORE INTO knowledge_page_tags (knowledge_page_id, tag_id) VALUES (?, ?)', (page_id, tag_id))

