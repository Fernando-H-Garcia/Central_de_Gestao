from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PySide6.QtCore import Qt, QRectF, Signal
import datetime
from typing import List

from gui.components.timeline.timeline_models import TimelineItem, TimelineEvent
from gui.components.timeline.timeline_geometry import TimelineGeometry
from gui.theme import (BG_PRIMARY, TEXT_PRIMARY, BORDER_SUBTLE, ACCENT_BLUE,
                   WARNING_ORANGE, get_status_color, SUCCESS_GREEN, ERROR_RED, TEXT_DISABLED)

_TOP_GAP = 0  # sem faixa — etiqueta HOJE foi movida para o header para não quebrar sincronia

class TimelineCanvas(QWidget):
    # Emitido quando uma tarefa é clicada (retorna o task_id)
    item_clicked = Signal(int)
    item_double_clicked = Signal(int)
    event_clicked = Signal(object)  # TimelineEvent
    task_moved = Signal(int, object, object)  # task_id, new_start_date, new_end_date
    # Emitido ao arrastar a linha do tempo (novo offset_x)
    pan_triggered = Signal(int)
    # Emitido quando o usuário roda o mouse sobre o canvas (delta) — a view repassa à árvore
    wheel_scrolled = Signal(int)

    def __init__(self, geometry: TimelineGeometry, parent=None):
        super().__init__(parent)
        self.geometry = geometry
        self._offset_x = 0
        
        self.items: List[TimelineItem] = []
        self.events: List[TimelineEvent] = []
        
        self.show_events = True
        self.show_alarms = True
        self._selected_id = None
        self._drag_bar = None  # {id, start, end, start_x, is_parent}
        
        # Habilita o rastreamento do mouse para tooltips de hover
        self.setMouseTracking(True)
        
        # Virtualization/Scroll helpers
        self._scroll_y = 0

    def set_selected(self, task_id):
        self._selected_id = task_id
        self.update()

    def _bar_color(self, item: TimelineItem) -> QColor:
        ds = getattr(item, 'display_status', item.status)
        if ds == "Concluído":
            return QColor(SUCCESS_GREEN)
        if ds == "ATRASADA" or ds == "Bloqueado":
            return QColor(ERROR_RED)
        if ds == "EM RISCO":
            return QColor(WARNING_ORANGE)
        if ds == "NÃO INICIADA":
            return QColor(TEXT_DISABLED)
        # Hierarquia: família por nível (só quando sem semântica de estado)
        lvl = getattr(item, 'level', 0)
        if lvl == 0:
            return QColor(ACCENT_BLUE)
        if lvl == 1:
            return QColor("#7c8cf0")
        return QColor("#a5b4fc")

    def set_data(self, items: List[TimelineItem], events: List[TimelineEvent] = None):
        """Define a lista plana de itens a serem renderizados (já resolvidos após expand/collapse)."""
        self.items = items
        self.events = events or []
        
        # Altura exatamente igual ao conteúdo (linhas de 40px, mesma da árvore)
        total_height = len(self.items) * self.geometry.row_height + _TOP_GAP
        self.setMinimumHeight(total_height)
        self.update()

    def set_scroll_y(self, value: int):
        """Espelha o scroll vertical da árvore (fonte única de rolagem)."""
        if value != self._scroll_y:
            self._scroll_y = value
            self.update()

    def set_offset_x(self, offset_x: int):
        self._offset_x = offset_x
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        try:
            # Fundo do Canvas (Futuro)
            painter.fillRect(event.rect(), QColor(BG_PRIMARY))
            # Distinção visual para o Passado (Fundo ligeiramente mais escuro e sutil)
            clip = event.rect()
            today = datetime.datetime.now()
            today_x = self.geometry.datetime_to_x(today)
            today_x_view = int(today_x - self._offset_x)
            if today_x_view > clip.left():
                past_width = min(today_x_view - clip.left(), clip.width())
                past_rect = QRectF(clip.left(), clip.top(), past_width, clip.height())
                painter.fillRect(past_rect, QColor("#06060c")) # Fundo do Passado
            # Desenhar linhas de grid vertical
            self._draw_grid(painter, clip)
            # Itens/eventos em coordenadas de CONTEÚDO, transladados pelo scroll da árvore
            painter.save()
            painter.translate(0, -self._scroll_y)
            # Desenhar itens (tarefas)
            self._draw_items(painter)
            # Desenhar eventos e alarmes
            self._draw_events(painter, clip)
            painter.restore()
            # Desenhar a linha de HOJE (coordenadas de tela — altura total)
            self._draw_today_line(painter, clip)
        finally:
            painter.end()

    def _hit_bar(self, pos):
        cy = pos.y() + self._scroll_y
        row = int((cy - _TOP_GAP) // self.geometry.row_height)
        if 0 <= row < len(self.items):
            item = self.items[row]
            if item.is_parent or item.is_milestone:
                return None
            eff_start = item.manual_start or item.start
            eff_end = item.manual_end or item.end
            if eff_start and eff_end:
                x1 = self.geometry.date_to_x(eff_start) - self._offset_x
                x2 = self.geometry.date_to_x(eff_end + datetime.timedelta(days=1)) - self._offset_x
                if x1 - 4 <= pos.x() <= x2 + 4:
                    return item
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.position()
            hit = self._hit_bar(pos)
            if hit is not None:
                eff_start = hit.manual_start or hit.start
                eff_end = hit.manual_end or hit.end
                self._drag_bar = {
                    "id": hit.id,
                    "start": eff_start,
                    "end": eff_end,
                    "start_x": pos.x(),
                    "item": hit,
                }
                self._has_dragged = False
                self.setCursor(Qt.ClosedHandCursor)
                return
            self._is_dragging = True
            self._drag_start_x = pos.x()
            self._drag_start_offset_x = self._offset_x
            self._has_dragged = False

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            task_id = self._get_item_at(event.position().y() + self._scroll_y)
            if task_id:
                self.item_double_clicked.emit(task_id)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._drag_bar is not None:
                info = self._drag_bar
                self._drag_bar = None
                self.unsetCursor()
                # emite mesmo que delta 0, o host decide se persiste
                eff_start = info["item"].manual_start or info["item"].start
                eff_end = info["item"].manual_end or info["item"].end
                # só emite se arrastou >3px
                if self._has_dragged:
                    self.task_moved.emit(info["id"], eff_start, eff_end)
                else:
                    # clique na barra sem arrastar -> seleção
                    self._selected_id = info["id"]
                    self.update()
                    self.item_clicked.emit(info["id"])
                self._has_dragged = False
                return
            self._is_dragging = False
            # Se não moveu o mouse significativamente, trata como clique
            if not self._has_dragged:
                # Prioridade: evento/alarme sob o cursor
                ev = self._get_event_at(event.position())
                if ev is not None:
                    self.event_clicked.emit(ev)
                    return
                task_id = self._get_item_at(event.position().y() + self._scroll_y)
                if task_id:
                    self._selected_id = task_id
                    self.update()
                    self.item_clicked.emit(task_id)

    def mouseMoveEvent(self, event):
        pos = event.position()
        
        # Barra sendo arrastada — move a tarefa no tempo
        if self._drag_bar is not None:
            delta_x = pos.x() - self._drag_bar["start_x"]
            if abs(delta_x) > 3:
                self._has_dragged = True
            delta_days = int(round(delta_x / self.geometry.pixels_per_day))
            if delta_days != 0 or self._has_dragged:
                # atualiza visualmente o item arrastado
                orig_start = self._drag_bar["start"]
                orig_end = self._drag_bar["end"]
                new_start = orig_start + datetime.timedelta(days=delta_days)
                new_end = orig_end + datetime.timedelta(days=delta_days)
                item = self._drag_bar["item"]
                # folha usa start/end
                item.start = new_start
                item.end = new_end
                self.update()
            return
        # Lógica de Pan/Drag horizontal
        if getattr(self, '_is_dragging', False):
            delta_x = pos.x() - self._drag_start_x
            if abs(delta_x) > 5:
                self._has_dragged = True
            new_offset = int(self._drag_start_offset_x - delta_x)
            self.pan_triggered.emit(new_offset)
            return

        # Cursor de arrasto sobre barra
        if self._drag_bar is None:
            if self._hit_bar(pos) is not None:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.unsetCursor()

        # Encontra o item sob o cursor de mouse
        pos = event.position()
        cy = pos.y() + self._scroll_y
        row = int((cy - _TOP_GAP) // self.geometry.row_height)
        
        from PySide6.QtWidgets import QToolTip
        
        # --- Prioridade: Eventos e Alarmes primeiro (ícones pequenos, difíceis de clicar) ---
        task_y_map = {}
        for i, item in enumerate(self.items):
            task_y_map[item.id] = _TOP_GAP + i * self.geometry.row_height
            
        for ev in self.events:
            if ev.event_type == "event" and not self.show_events:
                continue
            if ev.event_type == "alarm" and not self.show_alarms:
                continue
                
            x_canvas = self.geometry.datetime_to_x(ev.datetime)
            x_view = int(x_canvas - self._offset_x)
            
            y = _TOP_GAP + 10
            if ev.task_id and ev.task_id in task_y_map:
                y = task_y_map[ev.task_id] + self.geometry.row_height // 2
                
            # Verifica proximidade do cursor (raio de 12px)
            dist_sq = (pos.x() - x_view)**2 + (cy - y)**2
            if dist_sq < 144: 
                desc = getattr(ev.raw_entity, 'description', '') or ''
                desc_line = f"<br/>Descrição: {desc}" if desc else ""
                
                type_name = "Alarme" if ev.event_type == "alarm" else "Evento"
                date_str = ev.datetime.strftime("%d/%m/%Y %H:%M")
                
                tooltip = (
                    f"<b>{type_name}: {ev.title}</b><br/>"
                    f"Horário: {date_str}"
                    f"{desc_line}"
                )
                QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
                return

        # --- Depois: barras de tarefa (mais largas, fáceis de alcançar em outra posição) ---
        if 0 <= row < len(self.items):
            item = self.items[row]
            eff_start = item.manual_start or item.start
            eff_end = item.manual_end or item.end
            
            if eff_start and eff_end:
                x1 = self.geometry.date_to_x(eff_start) - self._offset_x
                x2 = self.geometry.date_to_x(eff_end + datetime.timedelta(days=1)) - self._offset_x
                
                # Se o cursor X estiver no intervalo da barra
                if x1 <= pos.x() <= x2:
                    start_str = eff_start.strftime("%d/%m/%Y")
                    end_str = eff_end.strftime("%d/%m/%Y")
                    ds = getattr(item, 'display_status', item.status)
                    derived = getattr(item, 'derived_status', '')
                    extra = f"<br/>Estado: <b>{ds}</b>" if derived else ""
                    summ = getattr(item, 'summary_text', '')
                    summ_line = f"<br/>{summ}" if summ else ""
                    tooltip = (
                        f"<b>{item.title}</b><br/>"
                        f"Status: {item.status}{extra}<br/>"
                        f"Período: {start_str} até {end_str}<br/>"
                        f"Progresso: {int(item.progress)}%{summ_line}"
                    )
                    QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
                    return

        # Se não estiver sobre nenhuma barra, esconde o tooltip
        QToolTip.hideText()

    def wheelEvent(self, event):
        # Repassa a rolagem do mouse à árvore (fonte única de scroll vertical)
        self.wheel_scrolled.emit(event.angleDelta().y())

    def _get_event_at(self, pos):
        cy = pos.y() + self._scroll_y
        task_y_map = {}
        for i, item in enumerate(self.items):
            task_y_map[item.id] = _TOP_GAP + i * self.geometry.row_height
        for ev in self.events:
            if ev.event_type == "event" and not self.show_events:
                continue
            if ev.event_type == "alarm" and not self.show_alarms:
                continue
            x_canvas = self.geometry.datetime_to_x(ev.datetime)
            x_view = int(x_canvas - self._offset_x)
            y = _TOP_GAP + 10
            if ev.task_id and ev.task_id in task_y_map:
                y = task_y_map[ev.task_id] + self.geometry.row_height // 2
            if (pos.x() - x_view)**2 + (cy - y)**2 < 144:
                return ev
        return None

    def _get_item_at(self, y: float) -> int:
        row = int((y - _TOP_GAP) // self.geometry.row_height)
        if 0 <= row < len(self.items):
            return self.items[row].id
        return None

    def _draw_grid(self, painter: QPainter, clip):
        ppd = self.geometry.pixels_per_day
        grid_top = clip.top()
        # Exclusivo por filtro: Semana → só semanas, Mês → só meses (usuário pediu demais não aparecerem)
        if ppd >= 30:
            mode = "day"   # Dia (50.0)
        elif ppd >= 10:
            mode = "week"  # Semana (15.0)
        else:
            mode = "month" # Mês (5.0)

        start_date = self.geometry.x_to_date(self._offset_x + clip.left())
        end_date = self.geometry.x_to_date(self._offset_x + clip.right())
        
        current_date = datetime.date(start_date.year, start_date.month, start_date.day)
        while current_date <= end_date + datetime.timedelta(days=1):
            x_canvas = self.geometry.date_to_x(current_date)
            x_view = int(x_canvas - self._offset_x)
            
            if mode == "month":
                if current_date.day == 1:
                    pen = QPen(QColor("#3a3a6a"))
                    pen.setWidth(2 if ppd <= 7 else 1)
                    painter.setPen(pen)
                    painter.drawLine(x_view, grid_top, x_view, clip.bottom())
            elif mode == "week":
                if current_date.weekday() == 0:
                    pen = QPen(QColor("#2a2a4a"))
                    pen.setWidth(1)
                    painter.setPen(pen)
                    painter.drawLine(x_view, grid_top, x_view, clip.bottom())
            else:  # day
                pen = QPen(QColor(BORDER_SUBTLE))
                pen.setStyle(Qt.DotLine)
                painter.setPen(pen)
                painter.drawLine(x_view, grid_top, x_view, clip.bottom())
            current_date += datetime.timedelta(days=1)

    def _draw_items(self, painter: QPainter):
        row_h = self.geometry.row_height
        # Faixa visível em coordenadas de conteúdo (o painter já está transladado por -_scroll_y)
        start_row = int(max(0, (self._scroll_y - _TOP_GAP) // row_h))
        end_row = int(min(len(self.items) - 1,
                          (self._scroll_y + self.height() - _TOP_GAP) // row_h + 1))
        
        for i in range(start_row, end_row + 1):
            item = self.items[i]
            y = _TOP_GAP + i * self.geometry.row_height
            
            # Linha horizontal sutil entre linhas
            painter.setPen(QPen(QColor(BORDER_SUBTLE)))
            painter.drawLine(0, y + self.geometry.row_height, self.width(), y + self.geometry.row_height)
            
            # Desenhar barra do item
            self._draw_bar(painter, item, y)

    def _draw_bar(self, painter: QPainter, item: TimelineItem, y: int):
        # Determina datas (Usa manual se houver, senao a derivada/start)
        eff_start = item.manual_start or item.start
        eff_end = item.manual_end or item.end
        
        if not eff_start and not eff_end:
            return  # Tarefa sem nenhuma data
            
        if eff_start and not eff_end:
            eff_end = eff_start
        elif eff_end and not eff_start:
            eff_start = eff_end
            
        # Calcular X1 e X2 no canvas
        x1_canvas = self.geometry.date_to_x(eff_start)
        # End date: a barra vai até o final do dia
        x2_canvas = self.geometry.date_to_x(eff_end + datetime.timedelta(days=1))
        
        x1_view = int(x1_canvas - self._offset_x)
        x2_view = int(x2_canvas - self._offset_x)
        
        bar_height = 20
        bar_y = y + (self.geometry.row_height - bar_height) // 2
        
        rect = QRectF(x1_view, bar_y, x2_view - x1_view, bar_height)
        
        # Se for milestore, desenhar losango em X2
        if item.is_milestone:
            painter.save()
            painter.setBrush(QColor(SUCCESS_GREEN))
            painter.setPen(Qt.NoPen)
            painter.translate(x2_view - 10, bar_y + bar_height//2)
            painter.rotate(45)
            painter.drawRect(-8, -8, 16, 16)
            painter.restore()
            # seleção no marco
            if self._selected_id == item.id:
                painter.save()
                pen = QPen(QColor("#ffffff"))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 4, 4)
                painter.restore()
            return

        base_color = self._bar_color(item)
        is_selected = (self._selected_id == item.id)
        
        painter.save()
        
        if item.is_parent:
            # Pai: barra de resumo — mais proeminente (10px) quando agregada,
            # tracejado com preenchimento translúcido quando manual
            if item.has_manual_dates():
                painter.setPen(QPen(base_color, 2, Qt.DashLine))
                painter.setBrush(QColor(base_color.red(), base_color.green(), base_color.blue(), 45))
                painter.drawRoundedRect(rect, 4, 4)
            else:
                rect = QRectF(x1_view, bar_y + (bar_height - 10)//2, x2_view - x1_view, 10)
                painter.setPen(Qt.NoPen)
                painter.setBrush(base_color)
                painter.drawRoundedRect(rect, 4, 4)
                # faixa de progresso no resumo do pai
                if item.progress > 0:
                    prog_w = (x2_view - x1_view) * (item.progress / 100.0)
                    prog_rect = QRectF(x1_view, bar_y + (bar_height - 10)//2, prog_w, 10)
                    painter.setBrush(base_color.darker(130))
                    painter.drawRoundedRect(prog_rect, 4, 4)
        else:
            painter.setPen(Qt.NoPen)
            painter.setBrush(base_color)
            painter.drawRoundedRect(rect, 4, 4)
            if item.progress > 0:
                prog_width = (x2_view - x1_view) * (item.progress / 100.0)
                prog_rect = QRectF(x1_view, bar_y, prog_width, bar_height)
                painter.setBrush(base_color.darker(120))
                painter.drawRoundedRect(prog_rect, 4, 4)

        if is_selected:
            pen = QPen(QColor("#ffffff"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            # contorno cobre a barra efetiva (pai 10px ou normal 20px)
            sel_rect = rect.adjusted(-2, -2, 2, 2)
            painter.drawRoundedRect(sel_rect, 5, 5)
            
        painter.restore()

    def _draw_events(self, painter: QPainter, clip):
        # Mapeia task_id para a linha Y (para centralizar o evento na linha da tarefa)
        task_y_map = {}
        for i, item in enumerate(self.items):
            task_y_map[item.id] = _TOP_GAP + i * self.geometry.row_height
            
        for ev in self.events:
            if ev.event_type == "event" and not self.show_events:
                continue
            if ev.event_type == "alarm" and not self.show_alarms:
                continue
                
            x_canvas = self.geometry.datetime_to_x(ev.datetime)
            x_view = int(x_canvas - self._offset_x)
            
            # Se tiver end_datetime (evento estendido)
            if ev.end_datetime and ev.event_type == "event":
                end_x_canvas = self.geometry.datetime_to_x(ev.end_datetime)
                end_x_view = int(end_x_canvas - self._offset_x)
            else:
                end_x_view = x_view

            y = _TOP_GAP + 10 # topo da faixa reservada
            if ev.task_id and ev.task_id in task_y_map:
                y = task_y_map[ev.task_id] + self.geometry.row_height // 2

            # Verifica visibilidade básica no X
            if x_view < clip.left() - 20 and end_x_view < clip.left() - 20:
                continue
            if x_view > clip.right() + 20 and end_x_view > clip.right() + 20:
                continue

            painter.save()
            if ev.event_type == "alarm":
                # Alarme: Sino ou triângulo amarelo (aumentado de 6 para 10 de raio)
                painter.setBrush(QColor(WARNING_ORANGE))
                painter.setPen(QColor(0, 0, 0))
                # Desenhar um triângulo maior
                from PySide6.QtGui import QPolygonF
                from PySide6.QtCore import QPointF
                poly = QPolygonF([
                    QPointF(x_view, y - 10),
                    QPointF(x_view - 9, y + 8),
                    QPointF(x_view + 9, y + 8)
                ])
                painter.drawPolygon(poly)
            else:
                # Evento: círculo cinza-acinzentado (não confundir com barra azul da tarefa)
                EVENT_GRAY = QColor("#9aa0b6")
                painter.setBrush(EVENT_GRAY)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(x_view - 6, y - 6, 12, 12)
                
                # Se tiver duração, desenha linha cinza
                if end_x_view > x_view:
                    pen = QPen(EVENT_GRAY)
                    pen.setWidth(2)
                    painter.setPen(pen)
                    painter.drawLine(x_view + 6, y, end_x_view - 6, y)
                    painter.drawEllipse(end_x_view - 6, y - 6, 12, 12)
                    
            painter.restore()

    def _draw_today_line(self, painter: QPainter, clip):
        today = datetime.datetime.now()
        x_canvas = self.geometry.datetime_to_x(today)
        x_view = int(x_canvas - self._offset_x)
        
        if clip.left() <= x_view <= clip.right():
            pen = QPen(QColor(ACCENT_BLUE))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawLine(x_view, clip.top(), x_view, clip.bottom())
