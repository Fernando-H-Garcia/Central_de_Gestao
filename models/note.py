from dataclasses import dataclass
from datetime import datetime
from .base import BaseModel

@dataclass
class Note(BaseModel):
    content: str = ""
    is_favorite: bool = False
    last_accessed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_archived: bool = False
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
