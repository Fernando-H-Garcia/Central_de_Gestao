from database.repositories.base_repository import BaseRepository
from models.task_dependency import TaskDependency
from database.connection import get_db_cursor
from typing import List

class TaskDependencyRepository(BaseRepository[TaskDependency]):
    def __init__(self):
        super().__init__('task_dependencies', TaskDependency)

    def create(self, dep: TaskDependency) -> TaskDependency:
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT INTO task_dependencies (task_id, depends_on_task_id, dependency_type, dependency_strength)
                VALUES (?, ?, ?, ?)
            ''', (dep.task_id, dep.depends_on_task_id, dep.dependency_type, dep.dependency_strength))
            dep.id = cursor.lastrowid
            return dep

    def get_all(self, include_archived=False, include_deleted=False) -> List[TaskDependency]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM task_dependencies")
            return [self._row_to_model(row) for row in cursor.fetchall()]

    def get_dependencies_for_task(self, task_id: int) -> List[TaskDependency]:
        """Returns dependencies where task_id requires depends_on_task_id."""
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM task_dependencies WHERE task_id = ?", (task_id,))
            return [self._row_to_model(row) for row in cursor.fetchall()]

    def get_dependents_for_task(self, task_id: int) -> List[TaskDependency]:
        """Returns dependencies where another task requires task_id (i.e. depends_on_task_id = task_id)."""
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM task_dependencies WHERE depends_on_task_id = ?", (task_id,))
            return [self._row_to_model(row) for row in cursor.fetchall()]

    def delete_dependency(self, task_id: int, depends_on_task_id: int):
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM task_dependencies WHERE task_id = ? AND depends_on_task_id = ?", (task_id, depends_on_task_id))
