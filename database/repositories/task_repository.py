from .base_repository import BaseRepository
from models.entities import Task
from database.connection import get_db_cursor

class TaskRepository(BaseRepository[Task]):
    def __init__(self):
        super().__init__("tasks", Task)

    def create(self, task: Task) -> Task:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO tasks (uuid, parent_task_id, project_id, title, context, energy_level, status, position, start_date, due_date, alert_date, alert_message, originated_from_idea_id, estimated_hours, is_milestone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task.uuid, task.parent_task_id, task.project_id, task.title, task.context, task.energy_level, task.status, task.position, task.start_date, task.due_date, task.alert_date, task.alert_message, task.originated_from_idea_id, task.estimated_hours, task.is_milestone))
            task.id = cursor.lastrowid
            return task

    def update(self, task: Task) -> Task:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE tasks 
                SET parent_task_id = ?, project_id = ?, title = ?, context = ?, energy_level = ?, status = ?, position = ?, is_favorite = ?, is_archived = ?, last_accessed_at = ?, start_date = ?, due_date = ?, alert_date = ?, alert_message = ?, completed_at = ?, originated_from_idea_id = ?, estimated_hours = ?, is_milestone = ?
                WHERE id = ?
            """, (task.parent_task_id, task.project_id, task.title, task.context, task.energy_level, task.status, task.position, task.is_favorite, task.is_archived, task.last_accessed_at, task.start_date, task.due_date, task.alert_date, task.alert_message, task.completed_at, task.originated_from_idea_id, task.estimated_hours, task.is_milestone, task.id))
            return task

    def get_tags(self, task_id: int) -> list:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT t.name FROM tags t
                JOIN task_tags tt ON t.id = tt.tag_id
                WHERE tt.task_id = ?
            ''', (task_id,))
            return [row[0] for row in cursor.fetchall()]

    def set_tags(self, task_id: int, tags: list):
        with get_db_cursor() as cursor:
            cursor.execute('DELETE FROM task_tags WHERE task_id = ?', (task_id,))
            for tag in tags:
                tag_name = tag.strip()
                if not tag_name:
                    continue
                cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                row = cursor.fetchone()
                if row:
                    tag_id = row[0]
                    cursor.execute('INSERT OR IGNORE INTO task_tags (task_id, tag_id) VALUES (?, ?)', (task_id, tag_id))

    def update_position(self, task_id: int, new_status: str, new_position: float):
        with get_db_cursor() as cursor:
            cursor.execute("UPDATE tasks SET status = ?, position = ? WHERE id = ?", (new_status, new_position, task_id))
