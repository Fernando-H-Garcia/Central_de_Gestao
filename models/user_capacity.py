from datetime import datetime
from typing import Optional

class UserCapacity:
    def __init__(
        self,
        date: str,
        available_hours: float,
        id: Optional[int] = None,
        created_at: Optional[str] = None
    ):
        self.id = id
        self.date = date
        self.available_hours = available_hours
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
