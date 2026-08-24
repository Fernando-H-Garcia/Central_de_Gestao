from typing import List
import datetime
from gui.components.timeline.timeline_models import TimelineItem

class TimelineAggregation:
    @staticmethod
    def aggregate_parent_dates(items: List[TimelineItem]):
        """
        Calcula as datas recursivamente. 
        Pai start = MIN(filhas start)
        Pai end = MAX(filhas end)
        Se a filha for pai, ela primeiro consolida as próprias filhas.
        """
        for item in items:
            TimelineAggregation._aggregate_item(item)

    @staticmethod
    def _aggregate_item(item: TimelineItem) -> tuple[datetime.date, datetime.date]:
        """
        Retorna (start, end) do item consolidado.
        """
        if not item.children:
            return item.start, item.end
            
        child_starts = []
        child_ends = []
        
        for child in item.children:
            c_start, c_end = TimelineAggregation._aggregate_item(child)
            # A prioridade é a data manual do filho, se houver, ou a data calculada/normal
            eff_start = child.manual_start or c_start
            eff_end = child.manual_end or c_end
            
            if eff_start:
                child_starts.append(eff_start)
            if eff_end:
                child_ends.append(eff_end)
                
        if child_starts:
            item.start = min(child_starts)
        if child_ends:
            item.end = max(child_ends)
            
        return item.start, item.end
