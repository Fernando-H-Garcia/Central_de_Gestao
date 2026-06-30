from datetime import datetime
from typing import Optional

class TaskDependency:
    def __init__(
        self,
        task_id: int,
        depends_on_task_id: int,
        dependency_type: str = 'finish_to_start',
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        dependency_strength: str = 'obrigatória'
    ):
        self.id = id
        self.task_id = task_id
        self.depends_on_task_id = depends_on_task_id
        self.dependency_type = dependency_type
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.dependency_strength = dependency_strength
