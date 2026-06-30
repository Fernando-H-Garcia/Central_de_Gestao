import json
from typing import List, Optional
from datetime import datetime
from models.entities import Task
from database.repositories.task_repository import TaskRepository
from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog

class TaskService:
    def __init__(self):
        self.task_repo = TaskRepository()
        self.log_repo = ActivityLogRepository()

    def _log_activity(self, entity_id: int, action: str, changes: dict = None):
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
        log = ActivityLog(entity_type="task", entity_id=entity_id, action=action, changed_fields_json=changes_json)
        self.log_repo.create(log)

    def create_task(self, title: str, context: str = None, energy_level: str = "Média", status: str = "Backlog", project_id: int = None, parent_task_id: int = None, start_date: datetime = None, due_date: datetime = None, alert_date: datetime = None, alert_message: str = None, estimated_hours: float = 0.0, is_milestone: bool = False) -> Task:
        print(f"[DEBUG TASK] create_task: title={title}, status={status}, project_id={project_id}")
        # Calcular posição para ficar no topo
        try:
            active_tasks = self.get_all_active()
        except Exception as e:
            print(f"[DEBUG TASK] get_all_active FAILED: {e}")
            import traceback
            traceback.print_exc()
            raise
        if project_id:
            active_tasks = [t for t in active_tasks if t.project_id == project_id]
        
        min_pos = min((t.position for t in active_tasks if t.position is not None), default=0.0)
        new_pos = min_pos - 1.0
        print(f"[DEBUG TASK] position: min_pos={min_pos}, new_pos={new_pos}")
        
        task = Task(title=title, context=context, energy_level=energy_level, status=status, project_id=project_id, parent_task_id=parent_task_id, start_date=start_date, due_date=due_date, alert_date=alert_date, alert_message=alert_message, estimated_hours=estimated_hours, is_milestone=is_milestone, position=new_pos)
        print(f"[DEBUG TASK] Task model created, fields={list(task.__dataclass_fields__.keys())}")
        print(f"[DEBUG TASK] Task.start_date={getattr(task, 'start_date', 'NOT SET')}")
        created_task = self.task_repo.create(task)
        print(f"[DEBUG TASK] repo.create returned id={created_task.id}")
        
        changes = {
            "title": {"from": None, "to": title},
            "due_date": {"from": None, "to": str(due_date).split(" ")[0] if due_date else None},
            "energy_level": {"from": None, "to": energy_level},
            "status": {"from": None, "to": status}
        }
        print(f"[DEBUG TASK] logging activity for task {created_task.id}")
        self._log_activity(created_task.id, "CREATED", changes)
        print(f"[DEBUG TASK] create_task done")
        return created_task

    def add_manual_activity(self, task_id: int, note: str):
        self._log_activity(task_id, "MANUAL_NOTE", {"note": note})

    def update_manual_activity(self, log_id: int, note: str):
        changes_json = json.dumps({"note": note}, ensure_ascii=False)
        self.log_repo.update_changed_fields(log_id, changes_json)

    def delete_activity(self, log_id: int):
        self.log_repo.delete(log_id)

    def update_task(self, task: Task, original_task: Task) -> Task:
        # Check if completed
        if task.status == "Concluído" and original_task.status != "Concluído":
            task.completed_at = datetime.now()
        elif task.status != "Concluído" and original_task.status == "Concluído":
            task.completed_at = None
            
        updated = self.task_repo.update(task)
        changes = {}
        for field in ["title", "context", "energy_level", "status", "project_id"]:
            old_val = getattr(original_task, field)
            new_val = getattr(task, field)
            if old_val != new_val:
                changes[field] = {"from": old_val, "to": new_val}
                
        if task.due_date != original_task.due_date:
            changes["due_date"] = {"from": str(original_task.due_date) if original_task.due_date else None, 
                                   "to": str(task.due_date) if task.due_date else None}
            
        if task.alert_date != original_task.alert_date:
            changes["alert_date"] = {"from": str(original_task.alert_date) if original_task.alert_date else None,
                                     "to": str(task.alert_date) if task.alert_date else None}
            
        if task.alert_message != original_task.alert_message:
            changes["alert_message"] = {"from": original_task.alert_message,
                                        "to": task.alert_message}
            
        if changes:
            self._log_activity(updated.id, "UPDATED", changes)

        # Quando uma tarefa é concluída, recalcular o status de bloqueio de todas
        # as tarefas que dependiam dela — elas podem ter sido desbloqueadas.
        if task.status == "Concluído" and original_task.status != "Concluído":
            try:
                from services.agenda_service import AgendaService
                agenda_svc = AgendaService()
                dependents = agenda_svc.dep_repo.get_dependents_for_task(task.id)
                for dep in dependents:
                    agenda_svc.recalculate_task_blocked_status(dep.task_id)
            except Exception as e:
                print(f"[TaskService] Erro ao recalcular dependentes após conclusão: {e}")
            
        return updated
        
    def update_task_position(self, task_id: int, new_position: float):
        task = self.task_repo.get_by_id(task_id)
        if task:
            task.position = new_position
            self.task_repo.update(task)

    def change_status(self, task: Task, new_status: str):
        import copy
        original = copy.deepcopy(task)
        task.status = new_status
        self.update_task(task, original)

    def get_all_active(self) -> List[Task]:
        from core.data_context import data_context
        snap = data_context.get_snapshot()
        if snap.tasks_by_id:
            return snap.get_all_active_tasks()
        return self.task_repo.get_all(include_archived=False, include_deleted=False)
        
    def get_tasks_by_project(self, project_id: int) -> List[Task]:
        from core.data_context import data_context
        snap = data_context.get_snapshot()
        if snap.tasks_by_id:
            return snap.get_tasks_by_project(project_id)
        return [t for t in self.get_all_active() if t.project_id == project_id and t.parent_task_id is None]
        
    def get_subtasks(self, parent_task_id: int) -> List[Task]:
        from core.data_context import data_context
        snap = data_context.get_snapshot()
        if snap.tasks_by_id:
            return snap.get_subtasks(parent_task_id)
        return [t for t in self.get_all_active() if t.parent_task_id == parent_task_id]
        
    def get_all_archived(self) -> List[Task]:
        all_tasks = self.task_repo.get_all(include_archived=True, include_deleted=False)
        return [t for t in all_tasks if t.is_archived]

    def archive_task(self, task_id: int):
        self.task_repo.archive(task_id)
        self._log_activity(task_id, "ARCHIVED")

    def restore_task(self, task_id: int):
        self.task_repo.restore(task_id)
        self._log_activity(task_id, "RESTORED")

    def soft_delete_task(self, task_id: int):
        # Antes de remover as dependências, coletar as tarefas que dependiam DESTA
        # para poder desblocá-las depois (elas perdem o bloqueador).
        from database.repositories.task_dependency_repository import TaskDependencyRepository
        dep_repo = TaskDependencyRepository()

        # Ids das tarefas que serão desbloqueadas após a exclusão desta
        dependents_to_unblock = [
            dep.task_id for dep in dep_repo.get_dependents_for_task(task_id)
        ]

        # Caso 1: esta tarefa depende de outras (ela é a "bloqueada")
        for dep in dep_repo.get_dependencies_for_task(task_id):
            dep_repo.delete_dependency(dep.task_id, dep.depends_on_task_id)

        # Caso 2: outras tarefas dependem desta (ela é a "bloqueadora")
        for dep in dep_repo.get_dependents_for_task(task_id):
            dep_repo.delete_dependency(dep.task_id, dep.depends_on_task_id)

        self.task_repo.soft_delete(task_id)
        self._log_activity(task_id, "DELETED")

        # Agora que as dependências foram removidas e a tarefa deletada,
        # recalcular o status das tarefas que eram bloqueadas por esta.
        # Como a bloqueadora já não existe mais, elas serão desbloqueadas.
        if dependents_to_unblock:
            try:
                from services.agenda_service import AgendaService
                agenda_svc = AgendaService()
                for tid in dependents_to_unblock:
                    agenda_svc.recalculate_task_blocked_status(tid)
            except Exception as e:
                print(f"[TaskService] Erro ao desbloquear dependentes após exclusão: {e}")
