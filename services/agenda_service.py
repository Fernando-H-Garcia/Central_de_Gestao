from database.repositories.agenda_repository import AgendaRepository
from database.repositories.task_dependency_repository import TaskDependencyRepository
from database.repositories.alert_repository import AlertRepository
from database.connection import get_db_cursor
from models.agenda_item import AgendaItem
from models.task_dependency import TaskDependency
from models.user_capacity import UserCapacity
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

class AgendaService:
    def __init__(self):
        self.agenda_repo = AgendaRepository()
        self.dep_repo = TaskDependencyRepository()
        self.alert_repo = AlertRepository()

    # --- Schedule Management ---
    def create_schedule(
        self,
        entity_type: str,
        entity_id: int,
        start_date: str,
        end_date: str,
        effort_hours: float = 0.0,
        schedule_status: str = 'planejado'
    ) -> AgendaItem:
        item = AgendaItem(
            entity_type=entity_type,
            entity_id=entity_id,
            start_date=start_date,
            end_date=end_date,
            effort_hours=effort_hours,
            schedule_status=schedule_status
        )
        return self.agenda_repo.create(item)

    def update_schedule(self, item: AgendaItem) -> AgendaItem:
        return self.agenda_repo.update(item)

    def delete_schedule(self, item_id: int):
        self.agenda_repo.delete(item_id)

    def get_schedules_for_entity(self, entity_type: str, entity_id: int) -> List[AgendaItem]:
        return self.agenda_repo.get_by_entity(entity_type, entity_id)

    def get_all_schedules(self) -> List[AgendaItem]:
        from core.data_context import data_context
        snap = data_context.get_snapshot()
        if snap.agenda_items_by_id:
            return snap.get_all_agenda_items()
        return self.agenda_repo.get_all()

    # --- Capacity & Effort Math ---
    def set_user_capacity(self, date_str: str, available_hours: float) -> UserCapacity:
        return self.agenda_repo.set_capacity(date_str, available_hours)

    def get_user_capacity(self, date_str: str) -> float:
        cap = self.agenda_repo.get_capacity(date_str)
        if cap:
            return cap.available_hours
        # Default capacity: 8 hours on weekdays, 0 hours on weekends
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if dt.weekday() >= 5: # Saturday/Sunday
                return 0.0
        except Exception:
            pass
        return 8.0

    def _get_dates_in_range(self, start_date_str: str, end_date_str: str) -> List[str]:
        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            dates = []
            curr = start_dt
            while curr <= end_dt:
                dates.append(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
            return dates
        except Exception:
            return [start_date_str]

    def get_total_planned_hours_for_date(self, date_str: str) -> float:
        """Calculates total planned effort hours for a date by distributing task efforts across their schedules."""
        total_hours = 0.0
        all_items = self.get_all_schedules()
        for item in all_items:
            if item.schedule_status == 'cancelado':
                continue
            dates = self._get_dates_in_range(item.start_date, item.end_date)
            if date_str in dates:
                # Distribute effort evenly over the planned duration days
                duration_days = len(dates)
                total_hours += item.effort_hours / max(1, duration_days)
        return total_hours

    def get_agenda_metrics_for_dates(self, date_strs: List[str]) -> Dict[str, Dict[str, float]]:
        """Batch fetches capacities and calculates planned effort distribution in-memory for a list of date strings."""
        if not date_strs:
            return {}

        # 1. Batch fetch capacities
        placeholders = ",".join("?" for _ in date_strs)
        capacities = {}
        with get_db_cursor() as cursor:
            cursor.execute(f"SELECT date, available_hours FROM user_capacity WHERE date IN ({placeholders})", date_strs)
            for row in cursor.fetchall():
                capacities[row['date']] = row['available_hours']

        # Construct metrics dictionary with defaults
        metrics = {}
        for d_str in date_strs:
            cap = capacities.get(d_str)
            if cap is None:
                try:
                    dt = datetime.strptime(d_str, "%Y-%m-%d")
                    cap = 0.0 if dt.weekday() >= 5 else 8.0
                except Exception:
                    cap = 8.0
            metrics[d_str] = {"capacity": cap, "planned": 0.0}

        # 2. Fetch all schedules once and calculate distribution in memory
        all_items = self.get_all_schedules()
        for item in all_items:
            if item.schedule_status == 'cancelado':
                continue
            item_dates = self._get_dates_in_range(item.start_date, item.end_date)
            overlap_dates = [d for d in item_dates if d in metrics]
            if overlap_dates:
                duration_days = max(1, len(item_dates))
                daily_effort = item.effort_hours / duration_days
                for d in overlap_dates:
                    metrics[d]["planned"] += daily_effort

        return metrics

    def _get_task_title(self, task_id: int) -> str:
        """Helper: retorna o título de uma tarefa pelo id."""
        with get_db_cursor() as cursor:
            cursor.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return row['title'] if row else f"Tarefa #{task_id}"

    def _log_task_activity(self, task_id: int, action: str, changes: dict = None):
        """Helper: registra uma entrada no ActivityLog para a tarefa informada."""
        import json
        from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
        log = ActivityLog(
            entity_type="task",
            entity_id=task_id,
            action=action,
            changed_fields_json=changes_json
        )
        ActivityLogRepository().create(log)

    # --- Dependency Tree math ---
    def add_dependency(self, task_id: int, depends_on_task_id: int, dependency_type: str = 'finish_to_start', dependency_strength: str = 'obrigatória') -> TaskDependency:
        # Prevent self-dependency
        if task_id == depends_on_task_id:
            raise ValueError("Uma tarefa não pode depender de si mesma.")
        
        dep = TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id, dependency_type=dependency_type, dependency_strength=dependency_strength)
        result = self.dep_repo.create(dep)

        # Registrar no log de atividades da tarefa dependente
        blocker_title = self._get_task_title(depends_on_task_id)
        self._log_task_activity(task_id, "DEPENDENCY_ADDED", {
            "depends_on_task_id": depends_on_task_id,
            "depends_on_title": blocker_title,
            "dependency_strength": dependency_strength
        })

        # Recalcular status: se a bloqueadora não estiver concluída → status = "Bloqueado"
        self.recalculate_task_blocked_status(task_id)

        return result

    def remove_dependency(self, task_id: int, depends_on_task_id: int):
        # Registrar no log antes de remover (enquanto ainda temos o título)
        blocker_title = self._get_task_title(depends_on_task_id)
        self._log_task_activity(task_id, "DEPENDENCY_REMOVED", {
            "depends_on_task_id": depends_on_task_id,
            "depends_on_title": blocker_title
        })
        self.dep_repo.delete_dependency(task_id, depends_on_task_id)
        # Recalcular: a remoção pode ter desbloqueado a tarefa.
        self.recalculate_task_blocked_status(task_id)

    def get_dependency_tree(self, task_id: int, visited=None) -> Dict[str, Any]:
        """Returns recursive dictionary representing parent tasks this task depends on."""
        if visited is None:
            visited = set()
        
        if task_id in visited:
            return {"task_id": task_id, "cyclic_error": True, "dependencies": []}
        
        visited.add(task_id)
        
        # Get task details
        task_title = "Desconhecida"
        task_status = "Backlog"
        with get_db_cursor() as cursor:
            cursor.execute("SELECT title, status FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                task_title = row['title']
                task_status = row['status']

        dependencies = self.dep_repo.get_dependencies_for_task(task_id)
        children_trees = []
        for dep in dependencies:
            children_trees.append({
                "dependency_type": dep.dependency_type,
                "dependency_strength": dep.dependency_strength,
                "tree": self.get_dependency_tree(dep.depends_on_task_id, visited.copy())
            })

        return {
            "task_id": task_id,
            "title": task_title,
            "status": task_status,
            "dependencies": children_trees
        }

    def is_task_blocked(self, task_id: int) -> bool:
        """Returns True if this task has incomplete 'obrigatória' dependencies (excluindo tarefas deletadas)."""
        dependencies = self.dep_repo.get_dependencies_for_task(task_id)
        for dep in dependencies:
            if dep.dependency_strength != 'obrigatória':
                continue
            # Ignora tarefas bloqueadoras que foram deletadas
            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM tasks WHERE id = ? AND deleted_at IS NULL",
                    (dep.depends_on_task_id,)
                )
                row = cursor.fetchone()
                if row and row['status'] != 'Concluído':
                    return True
        return False

    def recalculate_task_blocked_status(self, task_id: int):
        """Atualiza automaticamente o campo 'status' da tarefa no banco de dados
        com base nas dependências obrigatórias vigentes:
          - Se tem dependência obrigatória incompleta → status = 'Bloqueado'
            (exceto se a tarefa estiver 'Pausado' — status manual que tem prioridade)
          - Se não tem bloqueios e status era 'Bloqueado' → status = 'A Fazer'
        Registra a mudança automática no ActivityLog da tarefa.
        """
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT status FROM tasks WHERE id = ? AND deleted_at IS NULL",
                (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                return  # Tarefa não existe ou foi deletada
            current_status = row['status']

        blocked = self.is_task_blocked(task_id)

        # 'Pausado' e 'Aguardando' são status manuais com prioridade sobre o auto-bloqueio.
        if current_status in ('Pausado', 'Aguardando'):
            return

        if blocked and current_status != 'Bloqueado':
            # Bloquear: descobre quem está bloqueando para registrar no log
            blocker_titles = []
            for dep in self.dep_repo.get_dependencies_for_task(task_id):
                if dep.dependency_strength == 'obrigatória':
                    with get_db_cursor() as cursor:
                        cursor.execute(
                            "SELECT title, status FROM tasks WHERE id = ? AND deleted_at IS NULL",
                            (dep.depends_on_task_id,)
                        )
                        r = cursor.fetchone()
                        if r and r['status'] != 'Concluído':
                            blocker_titles.append(r['title'])

            with get_db_cursor() as cursor:
                cursor.execute(
                    "UPDATE tasks SET status = 'Bloqueado' WHERE id = ?",
                    (task_id,)
                )
            self._log_task_activity(task_id, "STATUS_AUTO_CHANGED", {
                "status": {"from": current_status, "to": "Bloqueado"},
                "reason": "Bloqueado por dependência obrigatória",
                "blocking_tasks": blocker_titles
            })

        if not is_blocked and current_status == "Bloqueado":
            with get_db_cursor() as cursor:
                cursor.execute(
                    "UPDATE tasks SET status = 'Pendente' WHERE id = ?",
                    (task_id,)
                )
            self._log_task_activity(task_id, "STATUS_AUTO_CHANGED", {
                "status": {"from": "Bloqueado", "to": "Pendente"},
                "reason": "Dependência resolvida - tarefa desbloqueada automaticamente"
            })

    def is_task_blocking(self, task_id: int) -> bool:
        """Returns True if another incomplete task has an 'obrigatória' dependency on this task."""
        dependents = self.dep_repo.get_dependents_for_task(task_id)
        for dep in dependents:
            if dep.dependency_strength != 'obrigatória':
                continue
            with get_db_cursor() as cursor:
                cursor.execute("SELECT status FROM tasks WHERE id = ?", (dep.task_id,))
                row = cursor.fetchone()
                if row and row['status'] != 'Concluído':
                    return True
        return False

    # --- Alerts Integration ---
    def get_items_with_alerts(self) -> List[Dict[str, Any]]:
        """Returns all schedule items that have active alerts."""
        results = []
        all_items = self.get_all_schedules()
        for item in all_items:
            # Get alerts for this scheduled entity
            with get_db_cursor() as cursor:
                cursor.execute("SELECT * FROM alerts WHERE entity_type = ? AND entity_id = ? AND status = 'pending'", (item.entity_type, item.entity_id))
                alerts = cursor.fetchall()
                if alerts:
                    results.append({
                        "schedule_item": item,
                        "alerts": [dict(a) for a in alerts]
                    })
        return results
