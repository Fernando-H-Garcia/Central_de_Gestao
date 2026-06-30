import json
from typing import List, Optional
from models.entities import KnowledgePage
from database.repositories.knowledge_page_repository import KnowledgePageRepository
from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog

class KnowledgePageService:
    def __init__(self):
        self.page_repo = KnowledgePageRepository()
        self.log_repo = ActivityLogRepository()

    def _log_activity(self, entity_id: int, action: str, changes: dict = None):
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else None
        log = ActivityLog(entity_type="knowledge_page", entity_id=entity_id, action=action, changed_fields_json=changes_json)
        self.log_repo.create(log)

    def create_page(self, title: str, content: str = None, parent_id: int = None, category: str = None, is_favorite: bool = False, last_reviewed_at: str = None, review_interval_days: int = None) -> KnowledgePage:
        page = KnowledgePage(title=title, content=content, parent_id=parent_id, category=category, is_favorite=is_favorite, last_reviewed_at=last_reviewed_at, review_interval_days=review_interval_days)
        created_page = self.page_repo.create(page)
        self._log_activity(created_page.id, "CREATED", {"title": {"from": None, "to": title}})
        return created_page

    def update_page(self, page: KnowledgePage, original_page: KnowledgePage) -> KnowledgePage:
        updated = self.page_repo.update(page)
        changes = {}
        for field in ["title", "content", "parent_id", "category", "is_favorite", "last_reviewed_at", "review_interval_days"]:
            old_val = getattr(original_page, field)
            new_val = getattr(page, field)
            if old_val != new_val:
                changes[field] = {"from": old_val, "to": new_val}
        if changes:
            self._log_activity(page.id, "UPDATED", changes)
        return updated

    def get_by_id(self, page_id: int) -> Optional[KnowledgePage]:
        return self.page_repo.get_by_id(page_id)

    def get_all_active(self) -> List[KnowledgePage]:
        return self.page_repo.get_all(include_archived=False, include_deleted=False)

    def get_all_archived(self) -> List[KnowledgePage]:
        all_pages = self.page_repo.get_all(include_archived=True, include_deleted=False)
        return [p for p in all_pages if p.is_archived]

    def archive_page(self, page_id: int):
        self.page_repo.archive(page_id)
        self._log_activity(page_id, "ARCHIVED")

    def restore_page(self, page_id: int):
        self.page_repo.restore(page_id)
        self._log_activity(page_id, "RESTORED")

    def soft_delete_page(self, page_id: int):
        self.page_repo.soft_delete(page_id)
        self._log_activity(page_id, "DELETED")

    def get_tags(self, page_id: int) -> List[str]:
        return self.page_repo.get_tags_for_page(page_id)

    def set_tags(self, page_id: int, tags: List[str]):
        self.page_repo.set_tags_for_page(page_id, tags)
        self._log_activity(page_id, "TAGS_UPDATED", {"tags": tags})

