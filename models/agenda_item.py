from datetime import datetime
from typing import Optional

class AgendaItem:
    def __init__(
        self,
        entity_type: str,
        entity_id: int,
        start_date: str,
        end_date: str,
        effort_hours: float = 0.0,
        schedule_status: str = 'planejado',
        id: Optional[int] = None,
        created_at: Optional[str] = None
    ):
        self.id = id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.start_date = start_date
        self.end_date = end_date
        self.effort_hours = effort_hours
        self.schedule_status = schedule_status
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
