from dataclasses import dataclass
from datetime import datetime
from .base import BaseModel

@dataclass
class Idea(BaseModel):
    title: str = ""
    description: str = ""
    project_id: int | None = None
    category: str = ""
    interest_level: int = 3
    status: str = "Pendente"
    priority: str = "Média"  # Crítica, Alta, Média, Baixa
    position: float | None = None
    is_favorite: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_archived: bool = False
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
