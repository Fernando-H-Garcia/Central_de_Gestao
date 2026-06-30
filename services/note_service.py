import json
from database.repositories.note_repository import NoteRepository
from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog
from models.entities import Note
from typing import List, Optional

class NoteService:
    def __init__(self):
        self.repo = NoteRepository()
        self.log_repo = ActivityLogRepository()

    def _log(self, entity_id: int, action: str, changes: dict = None):
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
        log = ActivityLog(entity_type='note', entity_id=entity_id, action=action, changed_fields_json=changes_json)
        self.log_repo.create(log)

    def create(self, note: Note) -> Note:
        created = self.repo.create(note)
        self._log(created.id, 'CREATED', {'content': {'from': None, 'to': created.content}})
        return created

    def get(self, id: int) -> Optional[Note]:
        return self.repo.get_by_id(id)

    def list(self, include_archived: bool = False, include_deleted: bool = False) -> List[Note]:
        return self.repo.get_all(include_archived=include_archived, include_deleted=include_deleted)

    def get_all_archived(self) -> List[Note]:
        return [n for n in self.repo.get_all(include_archived=True, include_deleted=False) if n.is_archived]

    def get_by_project_id(self, project_id: int) -> List[Note]:
        """Return notes that belong to the project (excluding those linked to specific tasks)."""
        notes = self.repo.get_by_project_id(project_id)
        return [n for n in notes if n.task_id is None]

    def get_notes_by_task(self, task_id: int) -> List[Note]:
        """Return notes linked to a specific task."""
        return [n for n in self.list() if n.task_id == task_id]

    def update(self, note: Note) -> Note:
        updated = self.repo.update(note)
        self._log(updated.id, 'UPDATED', {'content': {'to': updated.content}})
        return updated

    def archive(self, id: int):
        self.repo.archive(id)
        self._log(id, 'ARCHIVED')

    def restore(self, id: int):
        self.repo.restore(id)
        self._log(id, 'RESTORED')

    def soft_delete(self, id: int):
        self.repo.soft_delete(id)
        self._log(id, 'DELETED')

