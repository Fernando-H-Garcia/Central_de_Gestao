import uuid
from datetime import datetime
from typing import Optional

class Alert:
    def __init__(
        self,
        entity_type: str,
        entity_id: int,
        title: str,
        alert_date: str,
        description: Optional[str] = None,
        alert_time: Optional[str] = None,
        priority: str = 'medium',
        status: str = 'pending',
        recurrence_type: str = 'none',
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        snoozed_until: Optional[str] = None,
        snooze_count: int = 0,
        recurrence_interval: Optional[int] = None,
        recurrence_count: Optional[int] = None,
        recurrence_group_id: Optional[str] = None
    ):
        self.id = id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.title = title
        self.description = description
        self.alert_date = alert_date
        self.alert_time = alert_time
        self.priority = priority
        self.status = status
        self.recurrence_type = recurrence_type
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.updated_at = updated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.snoozed_until = snoozed_until
        self.snooze_count = snooze_count
        self.recurrence_interval = recurrence_interval
        self.recurrence_count = recurrence_count
        self.recurrence_group_id = recurrence_group_id
