from dataclasses import dataclass, field
import uuid
from datetime import datetime
from typing import Optional

def generate_uuid() -> str:
    return str(uuid.uuid4())

@dataclass
class BaseModel:
    id: Optional[int] = None
    uuid: str = field(default_factory=generate_uuid)
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
