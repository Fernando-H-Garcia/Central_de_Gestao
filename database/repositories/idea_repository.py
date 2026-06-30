from .base_repository import BaseRepository
from models.entities import Idea
from database.connection import get_db_cursor

class IdeaRepository(BaseRepository[Idea]):
    def __init__(self):
        super().__init__('ideas', Idea)

    def create(self, idea: Idea) -> Idea:
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT INTO ideas (uuid, title, description, project_id, task_id, category, interest_level, status, priority, position, is_favorite, next_review_date, linked_project_id, linked_task_id, promoted_at, promoted_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (idea.uuid, idea.title, idea.description, idea.project_id, idea.task_id, idea.category, idea.interest_level, idea.status, idea.priority, idea.position, idea.is_favorite, idea.next_review_date, idea.linked_project_id, idea.linked_task_id, idea.promoted_at, idea.promoted_type))
            idea.id = cursor.lastrowid
            return idea

    def update(self, idea: Idea) -> Idea:
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE ideas
                SET title = ?, description = ?, project_id = ?, task_id = ?, category = ?, interest_level = ?, status = ?, priority = ?, position = ?, is_favorite = ?, next_review_date = ?, linked_project_id = ?, linked_task_id = ?, promoted_at = ?, promoted_type = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (idea.title, idea.description, idea.project_id, idea.task_id, idea.category, idea.interest_level, idea.status, idea.priority, idea.position, idea.is_favorite, idea.next_review_date, idea.linked_project_id, idea.linked_task_id, idea.promoted_at, idea.promoted_type, idea.id))
            return idea

    def get_tags(self, idea_id: int) -> list:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT t.name FROM tags t
                JOIN idea_tags it ON t.id = it.tag_id
                WHERE it.idea_id = ?
            ''', (idea_id,))
            return [row[0] for row in cursor.fetchall()]

    def set_tags(self, idea_id: int, tags: list):
        with get_db_cursor() as cursor:
            cursor.execute('DELETE FROM idea_tags WHERE idea_id = ?', (idea_id,))
            for tag in tags:
                tag_name = tag.strip()
                if not tag_name:
                    continue
                cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                row = cursor.fetchone()
                if row:
                    tag_id = row[0]
                    cursor.execute('INSERT OR IGNORE INTO idea_tags (idea_id, tag_id) VALUES (?, ?)', (idea_id, tag_id))
