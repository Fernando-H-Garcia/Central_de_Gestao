import json
from typing import List, Optional
from models.entities import Project
from database.repositories.project_repository import ProjectRepository
from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog
from database.connection import get_db_cursor

class ProjectService:
    def __init__(self):
        self.project_repo = ProjectRepository()
        self.log_repo = ActivityLogRepository()

    def _log_activity(self, entity_id: int, action: str, changes: dict = None):
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
        log = ActivityLog(entity_type="project", entity_id=entity_id, action=action, changed_fields_json=changes_json)
        self.log_repo.create(log)

    def create_project(self, name: str, objective: str = None, priority: str = "Média", due_date=None, alert_date=None, alert_message=None) -> Project:
        project = Project(name=name, objective=objective, priority=priority, due_date=due_date, alert_date=alert_date, alert_message=alert_message)
        created_project = self.project_repo.create(project)
        self._log_activity(created_project.id, "CREATED", {"name": {"from": None, "to": name}})
        return created_project

    def update_project(self, project: Project, original_project: Project) -> Project:
        updated = self.project_repo.update(project)
        changes = {}
        if project.status != original_project.status:
            changes["status"] = {"from": original_project.status, "to": project.status}
        if project.priority != original_project.priority:
            changes["priority"] = {"from": original_project.priority, "to": project.priority}
        if project.name != original_project.name:
            changes["name"] = {"from": original_project.name, "to": project.name}
        if project.objective != original_project.objective:
            changes["objective"] = {"from": original_project.objective, "to": project.objective}
        if project.due_date != original_project.due_date:
            changes["due_date"] = {"from": str(original_project.due_date) if original_project.due_date else None,
                                   "to": str(project.due_date) if project.due_date else None}
        if project.alert_date != original_project.alert_date:
            changes["alert_date"] = {"from": str(original_project.alert_date) if original_project.alert_date else None,
                                     "to": str(project.alert_date) if project.alert_date else None}
        if project.alert_message != original_project.alert_message:
            changes["alert_message"] = {"from": original_project.alert_message, "to": project.alert_message}
            
        if changes:
            self._log_activity(project.id, "UPDATED", changes)
            
        return updated

    def get_all_active(self) -> List[Project]:
        from core.data_context import data_context
        snap = data_context.get_snapshot()
        if snap.projects_by_id:
            return snap.get_all_active_projects()
        return self.project_repo.get_all(include_archived=False, include_deleted=False)
        
    def get_all_archived(self) -> List[Project]:
        all_projects = self.project_repo.get_all(include_archived=True, include_deleted=False)
        return [p for p in all_projects if p.is_archived]

    def archive_project(self, project_id: int):
        """Arquiva o projeto. Tarefas/ideias/notas permanecem intactas."""
        self.project_repo.archive(project_id)
        self._log_activity(project_id, "ARCHIVED")

    def restore_project(self, project_id: int):
        self.project_repo.restore(project_id)
        self._log_activity(project_id, "RESTORED")

    def soft_delete_project(self, project_id: int):
        """Envia o projeto para a lixeira e faz soft-delete em cascata de
        todas as tarefas, ideias e notas diretamente vinculadas."""
        with get_db_cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET deleted_at = CURRENT_TIMESTAMP WHERE project_id = ? AND deleted_at IS NULL",
                (project_id,)
            )
            cursor.execute(
                "UPDATE ideas SET deleted_at = CURRENT_TIMESTAMP WHERE project_id = ? AND deleted_at IS NULL",
                (project_id,)
            )
            cursor.execute(
                "UPDATE notes SET deleted_at = CURRENT_TIMESTAMP WHERE project_id = ? AND deleted_at IS NULL",
                (project_id,)
            )

        self.project_repo.soft_delete(project_id)
        self._log_activity(project_id, "DELETED")
