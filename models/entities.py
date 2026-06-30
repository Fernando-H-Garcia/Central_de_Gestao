from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from .base import BaseModel

@dataclass
class Project(BaseModel):
    name: str = ""
    objective: Optional[str] = None
    priority: str = "Média"
    health_status: str = "Verde"
    status: str = "Ativo"
    blocked_reason: Optional[str] = None
    blocked_since: Optional[datetime] = None
    is_favorite: bool = False
    last_accessed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    alert_date: Optional[datetime] = None
    alert_message: Optional[str] = None
    originated_from_idea_id: Optional[int] = None

@dataclass
class Task(BaseModel):
    title: str = ""
    parent_task_id: Optional[int] = None
    project_id: Optional[int] = None
    context: Optional[str] = None
    energy_level: str = "Média"
    status: str = "Pendente"
    position: Optional[float] = None
    is_favorite: bool = False
    last_accessed_at: Optional[datetime] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    alert_date: Optional[datetime] = None
    alert_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    originated_from_idea_id: Optional[int] = None
    estimated_hours: float = 0.0
    is_milestone: bool = False

@dataclass
class Idea(BaseModel):
    title: str = ""
    description: Optional[str] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    category: Optional[str] = None
    interest_level: int = 3
    status: str = "Nova"
    priority: str = "Média"
    position: Optional[float] = None
    is_favorite: bool = False
    next_review_date: Optional[datetime] = None
    linked_project_id: Optional[int] = None
    linked_task_id: Optional[int] = None
    promoted_at: Optional[datetime] = None
    promoted_type: Optional[str] = None

@dataclass
class Note(BaseModel):
    content: str = ""
    is_favorite: bool = False
    project_id: Optional[int] = None
    task_id: Optional[int] = None
    last_accessed_at: Optional[datetime] = None

@dataclass
class KnowledgePage(BaseModel):
    title: str = ""
    content: Optional[str] = None
    parent_id: Optional[int] = None
    category: Optional[str] = None
    is_favorite: bool = False
    last_accessed_at: Optional[datetime] = None
    last_reviewed_at: Optional[str] = None
    review_interval_days: Optional[int] = None


@dataclass
class Event(BaseModel):
    title: str = ""
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    description: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    project_id: Optional[int] = None
    task_id: Optional[int] = None

    # Events don't strictly inherit all BaseModel fields in the schema but it's safe to use them in the dataclass
    # for consistency, since the table has is_archived, archived_at, deleted_at, created_at.

@dataclass
class Setting:
    key: str
    value: str
@dataclass
class Attachment:
    id: Optional[int] = None
    uuid: str = ""
    entity_type: str = ""
    entity_id: int = 0
    file_path: str = ""
    file_name: str = ""
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

