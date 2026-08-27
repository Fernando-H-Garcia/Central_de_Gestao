from dataclasses import dataclass, field
from typing import List, Optional
import datetime

@dataclass
class TimelineItem:
    id: int
    parent_id: Optional[int]
    title: str
    level: int
    is_parent: bool
    is_expanded: bool
    
    # Datas calculadas (agregadas das filhas, se existirem)
    start: Optional[datetime.date] = None
    end: Optional[datetime.date] = None
    
    # Datas explicitamente definidas pelo usuário
    manual_start: Optional[datetime.date] = None
    manual_end: Optional[datetime.date] = None
    
    progress: float = 0.0
    status: str = "Pendente"
    priority: str = "Baixa"
    is_milestone: bool = False
    is_overdue: bool = False

    # Estados derivados (calculados no mapper)
    derived_status: str = ""          # "ATRASADA" | "Tempo esgotando" | "NÃO INICIADA" | ""
    display_status: str = ""          # estado efetivo usado na cor do canvas
    state_counts: dict = field(default_factory=dict)    # {status: n} de toda a subárvore
    derived_counts: dict = field(default_factory=dict)  # {estado_derivado: n} da subárvore
    progress_done: int = 0
    progress_total: int = 0
    summary_text: str = ""            # "3 tarefas · 2 concluídas · 67% · 21/08 → 09/09"
    
    # Referência à entidade original (caso precise abrir)
    raw_task: any = None

    # Prazo estimado (marcador vermelho na timeline)
    estimated_deadline: Optional[datetime.date] = None
    estimated_deadline_desc: Optional[str] = None

    children: List['TimelineItem'] = field(default_factory=list)
    
    def has_manual_dates(self) -> bool:
        return self.manual_start is not None or self.manual_end is not None

@dataclass
class TimelineEvent:
    id: int
    event_type: str  # "event" | "alarm"
    title: str
    datetime: datetime.datetime
    end_datetime: Optional[datetime.datetime] = None
    priority: str = "Média"
    task_id: Optional[int] = None
    project_id: Optional[int] = None
    raw_entity: any = None
