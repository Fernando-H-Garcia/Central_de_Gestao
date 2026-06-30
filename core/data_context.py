from typing import Dict, List, Any
import copy
from datetime import datetime

class DataSnapshot:
    """Immutable snapshot of the core database state for a given moment in time."""
    def __init__(self):
        self.tasks_by_id = {}
        self.projects_by_id = {}
        self.agenda_items_by_id = {}
        self.task_dependencies = []
        self.timestamp = datetime.now()
        
    def get_task(self, task_id):
        return self.tasks_by_id.get(task_id)
        
    def get_all_active_tasks(self):
        return list(self.tasks_by_id.values())
        
    def get_tasks_by_project(self, project_id):
        return [t for t in self.tasks_by_id.values() if t.project_id == project_id and t.parent_task_id is None]
        
    def get_subtasks(self, parent_task_id):
        return [t for t in self.tasks_by_id.values() if t.parent_task_id == parent_task_id]

    def get_all_active_projects(self):
        return list(self.projects_by_id.values())
        
    def get_project(self, project_id):
        return self.projects_by_id.get(project_id)
        
    def get_all_agenda_items(self):
        return list(self.agenda_items_by_id.values())


class DataContext:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataContext, cls).__new__(cls)
            cls._instance._current_snapshot = DataSnapshot()
        return cls._instance
        
    def get_snapshot(self) -> DataSnapshot:
        return self._current_snapshot
        
    def swap_snapshot(self, new_snapshot: DataSnapshot):
        self._current_snapshot = new_snapshot
        
data_context = DataContext()
