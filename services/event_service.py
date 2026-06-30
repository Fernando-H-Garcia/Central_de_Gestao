import json
from typing import List
from models.entities import Event
from database.repositories.event_repository import EventRepository
from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog

class EventService:
    def __init__(self):
        self.repo = EventRepository()
        self.log_repo = ActivityLogRepository()

    def _log(self, entity_id: int, action: str, changes: dict = None):
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
        log = ActivityLog(entity_type='event', entity_id=entity_id, action=action, changed_fields_json=changes_json)
        self.log_repo.create(log)

    def create(self, title: str, description: str = None, start: str = None, end: str = None, location: str = None, notes: str = None, project_id: int = None, task_id: int = None) -> Event:
        event = Event(title=title, description=description, start_datetime=start, end_datetime=end, location=location, notes=notes, project_id=project_id, task_id=task_id)
        created = self.repo.create(event)
        self._log(created.id, 'CREATED', {'title': {'from': None, 'to': title}})
        from core.event_bus import event_bus
        event_bus.emit('snapshot_updated', created)
        return created

    def update(self, event: Event, original: Event) -> Event:
        updated = self.repo.update(event)
        changes = {}
        for field in ['title', 'description', 'start_datetime', 'end_datetime', 'location', 'notes', 'project_id', 'task_id']:
            old = getattr(original, field)
            new = getattr(event, field)
            if old != new:
                changes[field] = {'from': old, 'to': new}
        if changes:
            self._log(event.id, 'UPDATED', changes)
        from core.event_bus import event_bus
        event_bus.emit('snapshot_updated', updated)
        return updated

    def archive(self, event_id: int):
        self.repo.archive(event_id)
        self._log(event_id, 'ARCHIVED')
        from core.event_bus import event_bus
        event_bus.emit('snapshot_updated', None)

    def restore(self, event_id: int):
        self.repo.restore(event_id)
        self._log(event_id, 'RESTORED')
        from core.event_bus import event_bus
        event_bus.emit('snapshot_updated', None)

    def delete(self, event_id: int):
        self.repo.soft_delete(event_id)
        self._log(event_id, 'DELETED')
        from core.event_bus import event_bus
        event_bus.emit('snapshot_updated', None)

    def list_active(self) -> List[Event]:
        return self.repo.get_all(include_archived=False, include_deleted=False)

    def list_archived(self) -> List[Event]:
        all_events = self.repo.get_all(include_archived=True, include_deleted=False)
        return [e for e in all_events if e.is_archived]

