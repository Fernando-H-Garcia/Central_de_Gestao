from .base_repository import BaseRepository
from models.entities import Project
from database.connection import get_db_cursor

class ProjectRepository(BaseRepository[Project]):
    def __init__(self):
        super().__init__("projects", Project)

    def create(self, project: Project) -> Project:
        with get_db_cursor() as cursor:
            cursor.execute("""
                INSERT INTO projects (uuid, name, objective, priority, health_status, status, due_date, alert_date, alert_message, originated_from_idea_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project.uuid, project.name, project.objective, project.priority, project.health_status, project.status, project.due_date, project.alert_date, project.alert_message, project.originated_from_idea_id))
            project.id = cursor.lastrowid
            return project
            
    def update(self, project: Project) -> Project:
        with get_db_cursor() as cursor:
            cursor.execute("""
                UPDATE projects 
                SET name = ?, objective = ?, priority = ?, health_status = ?, status = ?, blocked_reason = ?, blocked_since = ?, is_favorite = ?, is_archived = ?, last_accessed_at = ?, completed_at = ?, due_date = ?, alert_date = ?, alert_message = ?, originated_from_idea_id = ?
                WHERE id = ?
            """, (project.name, project.objective, project.priority, project.health_status, project.status, project.blocked_reason, project.blocked_since, project.is_favorite, project.is_archived, project.last_accessed_at, project.completed_at, project.due_date, project.alert_date, project.alert_message, project.originated_from_idea_id, project.id))
            return project

    def get_tags(self, project_id: int) -> list:
        with get_db_cursor() as cursor:
            cursor.execute('''
                SELECT t.name FROM tags t
                JOIN project_tags pt ON t.id = pt.tag_id
                WHERE pt.project_id = ?
            ''', (project_id,))
            return [row[0] for row in cursor.fetchall()]

    def set_tags(self, project_id: int, tags: list):
        with get_db_cursor() as cursor:
            cursor.execute('DELETE FROM project_tags WHERE project_id = ?', (project_id,))
            for tag in tags:
                tag_name = tag.strip()
                if not tag_name:
                    continue
                cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
                cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
                row = cursor.fetchone()
                if row:
                    tag_id = row[0]
                    cursor.execute('INSERT OR IGNORE INTO project_tags (project_id, tag_id) VALUES (?, ?)', (project_id, tag_id))
