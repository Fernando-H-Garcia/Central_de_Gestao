import json
from typing import List, Optional
from models.entities import Idea
from database.repositories.idea_repository import IdeaRepository
from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog

class IdeaService:
    def __init__(self):
        self.idea_repo = IdeaRepository()
        self.log_repo = ActivityLogRepository()

    def _log_activity(self, entity_id: int, action: str, changes: dict = None):
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
        log = ActivityLog(entity_type="idea", entity_id=entity_id, action=action, changed_fields_json=changes_json)
        self.log_repo.create(log)

    def create_idea(self, title: str, description: str = None, project_id: int = None, task_id: int = None, category: str = None, interest_level: int = 3, status: str = "Pendente", priority: str = "Média", next_review_date=None) -> Idea:
        idea = Idea(title=title, description=description, project_id=project_id, task_id=task_id, category=category, interest_level=interest_level, status=status, priority=priority, next_review_date=next_review_date)
        created_idea = self.idea_repo.create(idea)
        self._log_activity(created_idea.id, "CREATED", {"title": {"from": None, "to": title}})
        return created_idea

    def update_idea(self, idea: Idea, original_idea: Idea) -> Idea:
        updated = self.idea_repo.update(idea)
        changes = {}
        for field in ["title", "description", "project_id", "category", "interest_level", "status", "priority", "is_favorite"]:
            old_val = getattr(original_idea, field)
            new_val = getattr(idea, field)
            if old_val != new_val:
                changes[field] = {"from": old_val, "to": new_val}
        if changes:
            self._log_activity(idea.id, "UPDATED", changes)
        return updated

    def get_by_id(self, idea_id: int) -> Optional[Idea]:
        return self.idea_repo.get_by_id(idea_id)

    def get_all_active(self) -> List[Idea]:
        return self.idea_repo.get_all(include_archived=False, include_deleted=False)

    def get_ideas_by_task(self, task_id: int) -> List[Idea]:
        """Return ideas linked to a specific task."""
        return [i for i in self.get_all_active() if i.task_id == task_id]

    def get_ideas_by_project(self, project_id: int) -> List[Idea]:
        """Return ideas that belong to the project (excluding those linked to specific tasks)."""
        return [i for i in self.get_all_active() if i.project_id == project_id and i.task_id is None]



    def get_all_archived(self) -> List[Idea]:
        all_ideas = self.idea_repo.get_all(include_archived=True, include_deleted=False)
        return [i for i in all_ideas if i.is_archived]

    def archive_idea(self, idea_id: int):
        self.idea_repo.archive(idea_id)
        self._log_activity(idea_id, "ARCHIVED")

    def delete_idea(self, idea_id: int):
        self.idea_repo.delete(idea_id)
        
    def update_idea_position(self, idea_id: int, new_position: float):
        # We need a direct update or a generic update in repository
        # For simplicity, let's fetch, modify and update
        idea = self.idea_repo.get_by_id(idea_id)
        if idea:
            idea.position = new_position
            self.idea_repo.update(idea)
        self._log_activity(idea_id, "RESTORED")

    def restore_idea(self, idea_id: int):
        self.idea_repo.restore(idea_id)
        self._log_activity(idea_id, "RESTORED")

    def soft_delete_idea(self, idea_id: int):
        self.idea_repo.soft_delete(idea_id)
        self._log_activity(idea_id, "DELETED")

    def promote_to_project(self, idea_id: int, project_title: str, description_text: Optional[str], copy_tags: bool, copy_attachments: bool, link_idea: bool, priority: str = "Média", due_date=None, alert_date=None, alert_message=None) -> int:
        from services.project_service import ProjectService
        from database.connection import get_db_cursor
        from datetime import datetime
        
        idea = self.get_by_id(idea_id)
        if not idea:
            raise ValueError("Ideia não encontrada")
            
        proj_service = ProjectService()
        
        # Create Project
        proj = proj_service.create_project(name=project_title, objective=description_text, priority=priority, due_date=due_date, alert_date=alert_date, alert_message=alert_message)
        
        # Vínculo entre ideia e projeto
        if link_idea:
            proj.originated_from_idea_id = idea_id
            proj_service.project_repo.update(proj)
            
            idea.linked_project_id = proj.id
            idea.promoted_at = datetime.now()
            idea.promoted_type = "project"
            self.idea_repo.update(idea)
            
            from database.repositories.entity_link_repository import EntityLinkRepository
            EntityLinkRepository().add_link('idea', idea_id, 'project', proj.id, 'promoted_to')
            EntityLinkRepository().add_link('project', proj.id, 'idea', idea_id, 'originated_from')
            
        # Copy tags
        if copy_tags:
            tags = self.idea_repo.get_tags(idea_id)
            if tags:
                proj_service.project_repo.set_tags(proj.id, tags)
                
        # Copy attachments
        if copy_attachments:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT uuid, file_path, file_name, mime_type, file_size, checksum FROM attachments WHERE entity_type = 'idea' AND entity_id = ? AND deleted_at IS NULL", (idea_id,))
                attachments = cursor.fetchall()
                for att in attachments:
                    import uuid as uuid_lib
                    new_uuid = str(uuid_lib.uuid4())
                    cursor.execute("""
                        INSERT INTO attachments (uuid, entity_type, entity_id, file_path, file_name, mime_type, file_size, checksum)
                        VALUES (?, 'project', ?, ?, ?, ?, ?, ?)
                    """, (new_uuid, proj.id, att['file_path'], att['file_name'], att['mime_type'], att['file_size'], att['checksum']))
                    
        self._log_activity(idea_id, "PROMOTED_TO_PROJECT", {"project_id": proj.id, "project_title": project_title})
        return proj.id

    def promote_to_task(self, idea_id: int, task_title: str, description_text: Optional[str], copy_tags: bool, copy_attachments: bool, link_idea: bool, project_id: Optional[int] = None, priority: str = "Média", status: str = "Backlog", due_date=None, alert_date=None, alert_message=None) -> int:
        from services.task_service import TaskService
        from database.connection import get_db_cursor
        from datetime import datetime
        
        idea = self.get_by_id(idea_id)
        if not idea:
            raise ValueError("Ideia não encontrada")
            
        task_service = TaskService()
        
        # Create Task
        task = task_service.create_task(title=task_title, context=description_text, energy_level=priority, status=status, project_id=project_id, due_date=due_date, alert_date=alert_date, alert_message=alert_message)
        
        # Vínculo entre ideia e tarefa
        if link_idea:
            task.originated_from_idea_id = idea_id
            task_service.task_repo.update(task)
            
            idea.linked_task_id = task.id
            idea.promoted_at = datetime.now()
            idea.promoted_type = "task"
            self.idea_repo.update(idea)
            
            from database.repositories.entity_link_repository import EntityLinkRepository
            EntityLinkRepository().add_link('idea', idea_id, 'task', task.id, 'promoted_to')
            EntityLinkRepository().add_link('task', task.id, 'idea', idea_id, 'originated_from')
            
        # Copy tags
        if copy_tags:
            tags = self.idea_repo.get_tags(idea_id)
            if tags:
                task_service.task_repo.set_tags(task.id, tags)
                
        # Copy attachments
        if copy_attachments:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT uuid, file_path, file_name, mime_type, file_size, checksum FROM attachments WHERE entity_type = 'idea' AND entity_id = ? AND deleted_at IS NULL", (idea_id,))
                attachments = cursor.fetchall()
                for att in attachments:
                    import uuid as uuid_lib
                    new_uuid = str(uuid_lib.uuid4())
                    cursor.execute("""
                        INSERT INTO attachments (uuid, entity_type, entity_id, file_path, file_name, mime_type, file_size, checksum)
                        VALUES (?, 'task', ?, ?, ?, ?, ?, ?)
                    """, (new_uuid, task.id, att['file_path'], att['file_name'], att['mime_type'], att['file_size'], att['checksum']))
                    
        self._log_activity(idea_id, "PROMOTED_TO_TASK", {"task_id": task.id, "task_title": task_title})
        return task.id
