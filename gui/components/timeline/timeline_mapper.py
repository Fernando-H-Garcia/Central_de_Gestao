from typing import List, Dict, Any
import datetime

from gui.components.timeline.timeline_models import TimelineItem, TimelineEvent
from gui.components.timeline.timeline_aggregation import TimelineAggregation

class TimelineMapper:
    @staticmethod
    def map_tasks_to_timeline(tasks: List[Any], subtasks_by_parent: Dict[int, List[Any]]) -> List[TimelineItem]:
        """
        Converte uma lista de tarefas raízes e o dicionário de subtarefas em uma 
        hierarquia de TimelineItem.
        """
        def parse_date(date_str) -> datetime.date:
            if not date_str: return None
            try:
                dt = datetime.datetime.fromisoformat(str(date_str))
                return dt.date()
            except:
                try:
                    return datetime.datetime.strptime(str(date_str).split()[0], "%Y-%m-%d").date()
                except:
                    return None

        def _build_item(task: Any, depth: int) -> TimelineItem:
            children_raw = subtasks_by_parent.get(task.id, [])
            
            # Converter datas
            start_d = parse_date(getattr(task, 'start_date', None))
            end_d = parse_date(getattr(task, 'due_date', None))
            
            t_item = TimelineItem(
                id=task.id,
                parent_id=getattr(task, 'parent_task_id', None),
                title=task.title,
                level=depth,
                is_parent=len(children_raw) > 0,
                is_expanded=True, # Controle inicial
                status=task.status,
                priority=task.energy_level,
                is_milestone=getattr(task, 'is_milestone', False),
                estimated_deadline=parse_date(getattr(task, 'estimated_deadline', None)),
                raw_task=task
            )

            # Define se as datas são manuais (inseridas no próprio item) 
            # ou derivadas (as quais serão preenchidas na agregação depois)
            if t_item.is_parent:
                t_item.manual_start = start_d
                t_item.manual_end = end_d
            else:
                t_item.start = start_d
                t_item.end = end_d
                
            for child_task in children_raw:
                t_item.children.append(_build_item(child_task, depth + 1))

            # Estado derivado + agregação da subárvore (pós-ordem)
            TimelineMapper._finalize_states(t_item)
            return t_item

        timeline_items = []
        for root_task in tasks:
            timeline_items.append(_build_item(root_task, 0))

        # Agora aplicamos a agregação para preencher start/end dos pais
        TimelineAggregation.aggregate_parent_dates(timeline_items)

        # Recomputa estado derivado dos pais após agregação (span pode mudar)
        for item in timeline_items:
            TimelineMapper._recompute_derived(item)

        # A agregação de datas precisa vir antes do resumo (que usa o span do pai)
        for item in timeline_items:
            TimelineMapper._build_summary(item)

        return timeline_items

    @staticmethod
    def _finalize_states(t_item: TimelineItem):
        """
        Pós-ordem: calcula o estado derivado (ATRASADA / Tempo esgotando / NÃO INICIADA)
        e agrega as contagens de estados da subárvore para pais.
        """
        today = datetime.date.today()
        eff_end = t_item.manual_end or t_item.end
        eff_start = t_item.manual_start or t_item.start
        is_done = t_item.status == 'Concluído'

        # Estado derivado do próprio item
        derived = ""
        if not is_done:
            if eff_end is not None and eff_end < today:
                derived = "ATRASADA"
            elif eff_end is not None and (eff_end - today).days <= 3:
                derived = "Tempo esgotando"
            elif eff_start is None:
                derived = "NÃO INICIADA"
        t_item.derived_status = derived
        t_item.is_overdue = derived == "ATRASADA"

        # display_status: semântica de estado sobrepõe o status explícito
        if is_done:
            t_item.display_status = "Concluído"
        elif derived:
            t_item.display_status = derived
        else:
            t_item.display_status = t_item.status

        # Agregação da subárvore
        if not t_item.is_parent:
            state_counts = {t_item.status: 1} if t_item.status else {}
            derived_counts = {derived: 1} if derived else {}
            t_item.state_counts = state_counts
            t_item.derived_counts = derived_counts
            if t_item.status == 'Concluído':
                t_item.progress_done = 1
            t_item.progress_total = 1
            if is_done:
                t_item.progress = 100.0
            elif t_item.status == 'Em Andamento':
                t_item.progress = 50.0
            return

        # Pai: soma as contagens das filhas (pai não conta a si mesmo)
        state_counts = {}
        derived_counts = {}
        done = 0
        total = 0
        for c in t_item.children:
            for k, v in c.state_counts.items():
                state_counts[k] = state_counts.get(k, 0) + v
            for k, v in c.derived_counts.items():
                derived_counts[k] = derived_counts.get(k, 0) + v
            done += c.progress_done
            total += c.progress_total
        t_item.state_counts = state_counts
        t_item.derived_counts = derived_counts
        t_item.progress_done = done
        t_item.progress_total = total
        t_item.progress = (done / total) * 100 if total else 0.0

    @staticmethod
    def _recompute_derived(t_item: TimelineItem):
        today = datetime.date.today()
        is_done = t_item.status == 'Concluído'
        eff_end = t_item.manual_end or t_item.end
        eff_start = t_item.manual_start or t_item.start
        if t_item.is_parent:
            eff_end = t_item.end
            eff_start = t_item.start
        derived = ""
        if not is_done:
            if eff_end is not None and eff_end < today:
                derived = "ATRASADA"
            elif eff_end is not None and (eff_end - today).days <= 3:
                derived = "Tempo esgotando"
            elif eff_start is None:
                derived = "NÃO INICIADA"
        t_item.derived_status = derived
        t_item.is_overdue = derived == "ATRASADA"
        if is_done:
            t_item.display_status = "Concluído"
        elif derived:
            t_item.display_status = derived
        else:
            t_item.display_status = t_item.status
        for c in t_item.children:
            TimelineMapper._recompute_derived(c)

    @staticmethod
    def _build_summary(t_item: TimelineItem):
        """Monta o texto de resumo agregado exibido na linha da tarefa pai."""
        counts = t_item.state_counts
        derived = t_item.derived_counts
        total = t_item.progress_total
        done = t_item.progress_done

        parts = []
        if total:
            parts.append(f"{total} tarefa{'s' if total != 1 else ''}")
        if done:
            parts.append(f"{done} concluída{'s' if done != 1 else ''}")
        for key, label in (("Em Andamento", "em andamento"), ("Atrasada", "atrasada")):
            n = counts.get(key, 0) or derived.get("ATRASADA", 0)
            if n:
                parts.append(f"{n} {label}" + ("s" if n != 1 else ""))
        if total and done is not None:
            pct = int(round((done / total) * 100)) if total else 0
            parts.append(f"{pct}%")

        if t_item.start or t_item.end:
            fmt = lambda d: d.strftime("%d/%m") if d else "—"
            parts.append(f"{fmt(t_item.start)} → {fmt(t_item.end)}")

        t_item.summary_text = " · ".join(parts)

        for c in t_item.children:
            TimelineMapper._build_summary(c)

    @staticmethod
    def map_events_to_timeline(events: List[Any]) -> List[TimelineEvent]:
        timeline_events = []
        for e in events:
            if not e.start_datetime:
                continue
                
            try:
                dt = datetime.datetime.fromisoformat(str(e.start_datetime))
                end_dt = datetime.datetime.fromisoformat(str(e.end_datetime)) if getattr(e, 'end_datetime', None) else None
                
                timeline_events.append(TimelineEvent(
                    id=e.id,
                    event_type="event",
                    title=e.title,
                    datetime=dt,
                    end_datetime=end_dt,
                    priority=e.priority if hasattr(e, 'priority') else "Média",
                    task_id=e.task_id if hasattr(e, 'task_id') else None,
                    project_id=e.project_id if hasattr(e, 'project_id') else None,
                    raw_entity=e
                ))
            except:
                pass
        return timeline_events

    @staticmethod
    def map_alarms_to_timeline(alarms: List[Any]) -> List[TimelineEvent]:
        timeline_events = []
        for a in alarms:
            if not getattr(a, 'alert_date', None):
                continue
                
            try:
                date_str = str(a.alert_date)
                time_str = str(a.alert_time) if getattr(a, 'alert_time', None) else "00:00"
                if len(time_str) == 5:
                    dt_str = f"{date_str} {time_str}:00"
                else:
                    dt_str = f"{date_str} {time_str}"
                
                dt = datetime.datetime.fromisoformat(dt_str)
                
                # Para alarmes associados a tarefas, salvamos o task_id para posicioná-lo
                task_id = None
                project_id = None
                if a.entity_type == "task":
                    task_id = a.entity_id
                elif a.entity_type == "project":
                    project_id = a.entity_id

                timeline_events.append(TimelineEvent(
                    id=a.id,
                    event_type="alarm",
                    title=a.title, # No alert.py é title
                    datetime=dt,
                    end_datetime=None,
                    priority=a.priority if hasattr(a, 'priority') else "Média",
                    task_id=task_id,
                    project_id=project_id,
                    raw_entity=a
                ))
            except Exception as e:
                pass
        return timeline_events
