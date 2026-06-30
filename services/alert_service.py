import json
from typing import List, Optional
from models.alert import Alert
from database.repositories.alert_repository import AlertRepository
from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog

class AlertService:
    def __init__(self):
        self.alert_repo = AlertRepository()
        self.log_repo = ActivityLogRepository()

    def _log_activity(self, entity_id: int, action: str, changes: dict = None):
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
        log = ActivityLog(entity_type="alert", entity_id=entity_id, action=action, changed_fields_json=changes_json)
        self.log_repo.create(log)

    def create_alert(
        self,
        entity_type: str,
        entity_id: int,
        title: str,
        alert_date: str,
        description: Optional[str] = None,
        alert_time: Optional[str] = None,
        priority: str = 'medium',
        status: str = 'pending',
        recurrence_type: str = 'none'
    ) -> Alert:
        alert = Alert(
            entity_type=entity_type,
            entity_id=entity_id,
            title=title,
            alert_date=alert_date,
            description=description,
            alert_time=alert_time,
            priority=priority,
            status=status,
            recurrence_type=recurrence_type
        )
        created = self.alert_repo.create(alert)
        self._log_activity(created.id, "CREATED", {"title": {"from": None, "to": title}})
        return created

    def update_alert(self, alert: Alert, original: Alert) -> Alert:
        updated = self.alert_repo.update(alert)
        changes = {}
        for field in ["title", "description", "alert_date", "alert_time", "priority", "status", "recurrence_type"]:
            old_val = getattr(original, field)
            new_val = getattr(alert, field)
            if old_val != new_val:
                changes[field] = {"from": old_val, "to": new_val}
        if changes:
            self._log_activity(alert.id, "UPDATED", changes)
        return updated

    def delete_alert(self, alert_id: int):
        self.alert_repo.delete(alert_id)
        self._log_activity(alert_id, "DELETED")

    def get_alert(self, alert_id: int) -> Optional[Alert]:
        return self.alert_repo.get_by_id(alert_id)

    def get_alerts_for_date(self, date_str: str) -> List[Alert]:
        """Returns active/pending alerts for a specific date (YYYY-MM-DD)."""
        all_alerts = self.alert_repo.get_all(include_archived=True, include_deleted=False)
        return [a for a in all_alerts if a.alert_date == date_str and a.status == 'pending']

    def get_alerts_for_entity(self, entity_type: str, entity_id: int) -> List[Alert]:
        """Returns all alerts linked to a specific entity."""
        all_alerts = self.alert_repo.get_all(include_archived=True, include_deleted=False)
        return [a for a in all_alerts if a.entity_type == entity_type and a.entity_id == entity_id]

    def get_next_alert(self, entity_type: str, entity_id: int) -> Optional[Alert]:
        """Returns the next pending alert chronologically for an entity."""
        alerts = self.get_alerts_for_entity(entity_type, entity_id)
        pending_alerts = [a for a in alerts if a.status == 'pending']
        if not pending_alerts:
            return None
        # Sort by date, then time
        pending_alerts.sort(key=lambda a: (a.alert_date, a.alert_time or '23:59'))
        return pending_alerts[0]

    def get_next_alerts_for_entities(self, entity_type: str, entity_ids: List[int]) -> dict:
        """Batch fetches the next pending/overdue alert chronologically for a list of entity IDs."""
        if not entity_ids:
            return {}
            
        from database.connection import get_db_cursor
        placeholders = ",".join("?" for _ in entity_ids)
        query = f"""
            SELECT * FROM alerts 
            WHERE entity_type = ? 
              AND status IN ('pending', 'overdue') 
              AND entity_id IN ({placeholders})
            ORDER BY alert_date ASC, COALESCE(alert_time, '23:59') ASC
        """
        
        results = {}
        with get_db_cursor() as cursor:
            cursor.execute(query, [entity_type] + entity_ids)
            for row in cursor.fetchall():
                alert_obj = Alert(**dict(row))
                if alert_obj.entity_id not in results:
                    results[alert_obj.entity_id] = alert_obj
                    
        return results

    def get_upcoming_alerts(self, limit: int = 20) -> List[Alert]:
        """Returns all pending/overdue alerts ordered chronologically."""
        all_alerts = self.alert_repo.get_all(include_archived=True, include_deleted=False)
        pending = [a for a in all_alerts if a.status in ('pending', 'overdue')]
        pending.sort(key=lambda a: (a.alert_date, a.alert_time or '23:59'))
        return pending[:limit]

    def get_active_alarms_for_project(self, project_id: int, task_service) -> List[Alert]:
        """Returns all active (pending/overdue and past scheduled time) alarms for all tasks in a project."""
        tasks = task_service.get_tasks_by_project(project_id)
        active = []
        for t in tasks:
            active.extend(self.get_active_alerts_for_task(t.id))
        # Sort by priority weight then date
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        active.sort(key=lambda a: (priority_order.get(a.priority, 9), a.alert_date, a.alert_time or '23:59'))
        return active

    def mark_overdue_alerts(self):
        """Finds all pending alerts that are past their scheduled date/time and marks them as overdue."""
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        self.alert_repo.mark_overdue(current_date, current_time)

    def get_active_alerts_for_task(self, task_id: int) -> List[Alert]:
        """Returns all active (pending/overdue) alerts for a task that are past their scheduled time."""
        from datetime import datetime
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        
        alerts = self.get_alerts_for_entity("task", task_id)
        active_alerts = []
        for a in alerts:
            if a.status == 'overdue':
                active_alerts.append(a)
            elif a.status == 'pending':
                # Show if date is in the past, or date is today and no hour is set, or date is today and hour is past/now
                if a.alert_date < current_date:
                    active_alerts.append(a)
                elif a.alert_date == current_date:
                    if not a.alert_time or a.alert_time <= current_time:
                        active_alerts.append(a)
                        
        active_alerts.sort(key=lambda a: (a.alert_date, a.alert_time or '23:59'))
        return active_alerts

    def snooze_alert(self, alert_id: int, snooze_option: str) -> Optional[Alert]:
        """Postpones the alert by a duration, resets status to 'pending'."""
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        import copy
        from datetime import datetime, timedelta
        now = datetime.now()
        
        if snooze_option == "10min":
            delta = timedelta(minutes=10)
        elif snooze_option == "30min":
            delta = timedelta(minutes=30)
        elif snooze_option == "1h":
            delta = timedelta(hours=1)
        elif snooze_option == "1dia":
            delta = timedelta(days=1)
        elif snooze_option == "1semana":
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(minutes=10)
            
        new_time = now + delta
        original = copy.deepcopy(alert)
        alert.alert_date = new_time.strftime("%Y-%m-%d")
        alert.alert_time = new_time.strftime("%H:%M")
        alert.status = 'pending'
        
        updated = self.update_alert(alert, original)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated", {"entity_type": "alert", "entity_id": alert_id})
        return updated

    def complete_alert(self, alert_id: int) -> Optional[Alert]:
        """Marks an alert as completed."""
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        import copy
        original = copy.deepcopy(alert)
        alert.status = 'completed'
        updated = self.update_alert(alert, original)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated", {"entity_type": "alert", "entity_id": alert_id})
        return updated

    def complete_alert_silent(self, alert_id: int) -> Optional[Alert]:
        """Marks an alert as completed without emitting events (safe for modal popups)."""
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        import copy
        original = copy.deepcopy(alert)
        alert.status = 'completed'
        updated = self.alert_repo.update(alert)
        changes = {}
        for field in ["title", "description", "alert_date", "alert_time", "priority", "status", "recurrence_type"]:
            old_val = getattr(original, field)
            new_val = getattr(alert, field)
            if old_val != new_val:
                changes[field] = {"from": old_val, "to": new_val}
        if changes:
            self._log_activity(alert.id, "UPDATED", changes)
        return updated

    def snooze_alert_silent(self, alert_id: int, snooze_option: str) -> Optional[Alert]:
        """Snoozes without emitting events (safe for modal popups)."""
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        import copy
        from datetime import datetime, timedelta
        now = datetime.now()
        if snooze_option == "10min":
            delta = timedelta(minutes=10)
        elif snooze_option == "30min":
            delta = timedelta(minutes=30)
        elif snooze_option == "1h":
            delta = timedelta(hours=1)
        elif snooze_option == "1dia":
            delta = timedelta(days=1)
        elif snooze_option == "1semana":
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(minutes=10)
        new_time = now + delta
        original = copy.deepcopy(alert)
        alert.alert_date = new_time.strftime("%Y-%m-%d")
        alert.alert_time = new_time.strftime("%H:%M")
        alert.status = 'pending'
        updated = self.alert_repo.update(alert)
        changes = {}
        for field in ["title", "description", "alert_date", "alert_time", "priority", "status", "recurrence_type"]:
            old_val = getattr(original, field)
            new_val = getattr(alert, field)
            if old_val != new_val:
                changes[field] = {"from": old_val, "to": new_val}
        if changes:
            self._log_activity(alert.id, "UPDATED", changes)
        return updated

    def mark_alert_overdue(self, alert_id: int) -> Optional[Alert]:
        """Manually marks an alert as overdue (e.g. when popup is closed)."""
        alert = self.get_alert(alert_id)
        if not alert:
            return None
        if alert.status == 'overdue':
            return alert
        import copy
        original = copy.deepcopy(alert)
        alert.status = 'overdue'
        updated = self.update_alert(alert, original)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated", {"entity_type": "alert", "entity_id": alert_id})
        return updated

