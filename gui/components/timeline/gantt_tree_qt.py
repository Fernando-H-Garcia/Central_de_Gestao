"""
GanttTree — árvore de tarefas com a linha do tempo EMBUTIDA na própria árvore.

Substitui o par (árvore + canvas em QScrollArea) por UM ÚNICO widget:
- Coluna 0: título da tarefa
- Coluna 1: resumo
- Coluna 2: linha do tempo (barras pintadas por cima da árvore)

Não existe sincronização de scroll porque só há um widget/uma barra de rolagem.
"""
import datetime

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QToolTip, QHeaderView, QMenu
from PySide6.QtCore import Qt, Signal, QTimer, QRectF, QPointF, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPolygonF

from gui.components.timeline.timeline_models import TimelineItem, TimelineEvent
from gui.theme import (BORDER_SUBTLE, ACCENT_BLUE, WARNING_ORANGE,
                       SUCCESS_GREEN, ERROR_RED, TEXT_DISABLED)

ROW_HEIGHT = 25


def bar_color(item: TimelineItem) -> QColor:
    ds = getattr(item, 'display_status', item.status)
    if ds == "Concluído":
        return QColor(SUCCESS_GREEN)
    if ds == "ATRASADA" or ds == "Bloqueado":
        return QColor(ERROR_RED)
    if ds == "EM RISCO" or ds == "Tempo esgotando":
        return QColor(WARNING_ORANGE)
    if ds == "NÃO INICIADA":
        return QColor(TEXT_DISABLED)
    lvl = getattr(item, 'level', 0)
    if lvl == 0:
        return QColor(ACCENT_BLUE)
    if lvl == 1:
        return QColor("#7c8cf0")
    return QColor("#a5b4fc")


class GanttTree(QTreeWidget):
    item_double_clicked = Signal(int)      # task_id (compat)
    item_clicked = Signal(int)             # task_id
    event_clicked = Signal(object)         # TimelineEvent
    task_moved = Signal(int, object, object)
    pan_triggered = Signal(int)
    # Contexto/duplo clique: carrega o Task (raw_task); cai para int id se indisponível
    open_task_requested = Signal(object)
    edit_task_requested = Signal(object)
    # Criar alarme/evento vinculados à tarefa (menu de contexto)
    create_alarm_requested = Signal(object)
    create_event_requested = Signal(object)
    # Excluir alarme/evento (menu de contexto no ícone)
    delete_event_requested = Signal(object)
    # Prazo Estimado (marcador vermelho): mover, editar e excluir
    deadline_moved = Signal(int, object)       # task_id, nova data
    edit_deadline_requested = Signal(object)   # Task (raw) ou id
    delete_deadline_requested = Signal(object) # Task (raw) ou id
    # Prazo Estimado aberto pelo menu da tarefa na TIMELINE: traz a data sob o mouse
    edit_deadline_at_requested = Signal(object, object)  # Task (raw) ou id, datetime.date | None
    # Alarmes/Eventos: arraste (TimelineEvent, novo início, novo fim) e edição
    event_moved = Signal(object, object, object)
    edit_event_requested = Signal(object)
    # Ctrl + roda do mouse: zoom contínuo (proposta de pixels/dia)
    ctrl_zoom_requested = Signal(float)

    def __init__(self, geometry, parent=None):
        super().__init__(parent)
        self.geometry = geometry
        self._offset_x = 0
        self.events = []
        self.show_events = True
        self.show_alarms = True
        self.selected_item_id = None
        self._hover_item_id = None   # item sob o mouse (destaque hover)
        self._hover_ev = None        # evento/alarme sob o mouse (destaque hover)
        self._drag_bar = None   # {"item", "start", "end", "start_x"}
        self._drag_event = None  # {"ev", "start_x", "orig_dt", "orig_end", "snap_day"}
        self._drag_pos = None   # posição atual do mouse durante arraste (indicador flutuante)
        self._drag_deadline = None  # {"item", "orig", "cur", "start_x"} arraste do prazo estimado
        self._hover_deadline_id = None  # id da tarefa cujo marcador está em hover
        self._guide_x = None    # linha-guia vertical que segue o mouse na timeline
        # Tooltip persistente: QToolTip some pelo timeout do sistema — reexibimos
        # num timer enquanto o mouse continuar sobre o mesmo item
        self._tip_text = None
        self._tip_global = None
        self._tip_timer = QTimer(self)
        self._tip_timer.setInterval(1000)
        self._tip_timer.timeout.connect(self._refresh_tooltip)
        self._has_dragged = False
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_offset = 0

        self.setColumnCount(3)
        self.setHeaderLabels(["Tarefa", "Resumo", "Linha do Tempo"])
        self.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.header().setStretchLastSection(True)
        self.setColumnWidth(0, 280)
        self.setColumnWidth(1, 180)
        self.header().hide()

        self.setUniformRowHeights(True)
        self.setIndentation(16)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self.setSelectionBehavior(QTreeWidget.SelectRows)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        # duplo clique NÃO expande/recolhe — abre a edição da tarefa (pedido do usuário)
        self.setExpandsOnDoubleClick(False)

        self.setStyleSheet(f"""
            QTreeView::item {{ height: {ROW_HEIGHT}px; }}
        """)

        self.currentItemChanged.connect(self._on_current_changed)
        self.itemExpanded.connect(lambda _: self.viewport().update())
        self.itemCollapsed.connect(lambda _: self.viewport().update())

    def _on_current_changed(self, current, previous):
        t = current.data(0, Qt.UserRole) if current else None
        self.selected_item_id = t.id if t else None
        self.viewport().update()

    # ---------- geometria ----------

    def timeline_left(self) -> int:
        """X (em coords do viewport) onde começa a coluna da linha do tempo."""
        return self.columnWidth(0) + self.columnWidth(1)

    def set_offset_x(self, value: int):
        if value != self._offset_x:
            self._offset_x = value
            self.viewport().update()

    def set_events(self, events):
        self.events = events or []
        self.viewport().update()

    def _x_view(self, x_canvas: float) -> float:
        return self.timeline_left() + x_canvas - self._offset_x

    def _visible_rows(self):
        """Itens visíveis (não ocultos, ancestrais expandidos) com seus rects."""
        out = []

        def collect(item):
            for i in range(item.childCount()):
                child = item.child(i)
                r = self.visualItemRect(child)
                if not r.isNull() and r.height() > 0:
                    t = child.data(0, Qt.UserRole)
                    if t:
                        out.append((t, r))
                    collect(child)

        collect(self.invisibleRootItem())
        return out

    def _row_for_task(self, task_id):
        def find(item):
            for i in range(item.childCount()):
                child = item.child(i)
                t = child.data(0, Qt.UserRole)
                if t and t.id == task_id:
                    return child
                found = find(child)
                if found:
                    return found
            return None
        return find(self.invisibleRootItem())

    # ---------- paint ----------

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        try:
            vp = self.viewport().rect()
            col_x = self.timeline_left()
            tl_rect = QRectF(col_x, vp.top(), vp.width() - col_x, vp.height())
            if tl_rect.width() <= 0:
                return

            self._draw_past_shading(painter, tl_rect)
            self._draw_grid(painter, tl_rect)
            self._draw_bars(painter, tl_rect)
            self._draw_events(painter, tl_rect)
            self._draw_deadlines(painter, tl_rect)
            self._draw_today_line(painter, tl_rect)
            # linha-guia vertical que segue o mouse (com data/hora no topo)
            self._draw_mouse_guide(painter, tl_rect)
            # janeleinha flutuante com as datas da posição durante o arraste
            self._draw_drag_info(painter)
        finally:
            painter.end()

        # guias de parentesco pai↔filhos (por cima do fundo, sob os textos já pintados)
        self._draw_branch_guides()

    def _draw_branch_guides(self):
        painter = QPainter(self.viewport())
        try:
            pen = QPen(QColor("#3d3d5c"))
            pen.setWidth(1)
            painter.setPen(pen)
            indent_x = self.indentation()

            def draw_branch(item):
                if item.childCount() == 0 or not item.isExpanded():
                    return
                parent_rect = self.visualItemRect(item)
                last_rect = self.visualItemRect(item.child(item.childCount() - 1))
                if parent_rect.isNull() or last_rect.isNull():
                    return
                x = parent_rect.x() + indent_x // 2 + 3
                painter.drawLine(x, parent_rect.bottom(), x, last_rect.bottom())
                for i in range(item.childCount()):
                    c = item.child(i)
                    r = self.visualItemRect(c)
                    if r.isNull():
                        continue
                    painter.drawLine(x, r.center().y(), x + 6, r.center().y())
                    draw_branch(c)

            root = self.invisibleRootItem()
            for i in range(root.childCount()):
                draw_branch(root.child(i))
        finally:
            painter.end()

    def _draw_past_shading(self, painter: QPainter, tl_rect: QRectF):
        # LÓGICA INVERTIDA (pedido do usuário): o FUTURO (hoje → frente) fica escuro;
        # o passado mantém o fundo normal da timeline
        today_x = self._x_view(self.geometry.datetime_to_x(datetime.datetime.now()))
        if today_x < tl_rect.right():
            future_x = max(today_x, tl_rect.left())
            painter.fillRect(QRectF(future_x, tl_rect.top(),
                                    tl_rect.right() - future_x, tl_rect.height()),
                             QColor("#06060c"))

    def _draw_grid(self, painter: QPainter, tl_rect: QRectF):
        ppd = self.geometry.pixels_per_day
        if ppd >= 30:
            mode = "day"
        elif ppd >= 10:
            mode = "week"
        else:
            mode = "month"

        start_date = self.geometry.x_to_date(self._offset_x + tl_rect.left() - self.timeline_left())
        end_date = self.geometry.x_to_date(self._offset_x + tl_rect.right() - self.timeline_left())

        current_date = datetime.date(start_date.year, start_date.month, start_date.day)
        while current_date <= end_date + datetime.timedelta(days=1):
            x_view = self._x_view(self.geometry.date_to_x(current_date))
            if tl_rect.left() <= x_view <= tl_rect.right():
                if mode == "month" and current_date.day == 1:
                    pen = QPen(QColor("#3a3a6a"))
                    pen.setWidth(2 if ppd <= 7 else 1)
                    painter.setPen(pen)
                    painter.drawLine(int(x_view), int(tl_rect.top()), int(x_view), int(tl_rect.bottom()))
                elif mode == "week" and current_date.weekday() == 0:
                    pen = QPen(QColor("#2a2a4a"))
                    painter.setPen(pen)
                    painter.drawLine(int(x_view), int(tl_rect.top()), int(x_view), int(tl_rect.bottom()))
                elif mode == "day":
                    pen = QPen(QColor(BORDER_SUBTLE))
                    pen.setStyle(Qt.DotLine)
                    painter.setPen(pen)
                    painter.drawLine(int(x_view), int(tl_rect.top()), int(x_view), int(tl_rect.bottom()))
            current_date += datetime.timedelta(days=1)

    def _draw_bars(self, painter: QPainter, tl_rect: QRectF):
        # O preview do arraste já está em item.start/end (mutados no mouseMove) —
        # NÃO aplicar delta de novo aqui (causava a barra inteira deslocar no resize)
        for t_item, vrect in self._visible_rows():
            row_rect = QRectF(tl_rect.left(), vrect.y(), tl_rect.width(), vrect.height())
            self.draw_bar(painter, t_item, row_rect)

    @staticmethod
    def _add_month(d: datetime.date) -> datetime.date:
        """Mesmo dia do mês seguinte (clamp no último dia quando necessário)."""
        import calendar
        m = d.month % 12 + 1
        y = d.year + (1 if d.month == 12 else 0)
        day = min(d.day, calendar.monthrange(y, m)[1])
        return datetime.date(y, m, day)

    def draw_bar(self, painter: QPainter, item: TimelineItem, row_rect: QRectF):
        # Marco tem prioridade — mesmo quando é pai (tem subtarefas)
        if item.is_milestone:
            if not item.start and not item.end and not item.has_manual_dates():
                return
            eff_start = item.manual_start or item.start or item.end
            eff_end = item.manual_end or item.end or item.start
            self._draw_milestone(painter, item, row_rect, eff_start)
            return

        if item.is_parent:
            # Pai: barra usa as DATAS PRÓPRIAS dele (independente das filhas).
            # Se filhas tiverem prazo além do pai → EXTENSÃO DE AVISO (filhas estouram o prazo do pai).
            if not item.start and not item.end and not item.has_manual_dates():
                return
            own_s = item.manual_start or item.start or item.end
            own_e = item.manual_end or item.end or item.start
            agg_end = item.end  # agregado das filhas (mapper)
            self._draw_parent_bar(painter, item, row_rect, own_s, own_e)
            if agg_end and own_e and agg_end > own_e:
                self._draw_overrun_warning(painter, row_rect, own_e, agg_end)
            return

        eff_start = item.manual_start or item.start
        eff_end = item.manual_end or item.end

        if not eff_start and not eff_end:
            return
        if eff_start and not eff_end:
            eff_end = eff_start
        elif eff_end and not eff_start:
            eff_start = eff_end

        color = bar_color(item)
        is_selected = (self.selected_item_id == item.id)
        is_hovered = (self._hover_item_id == item.id)

        painter.save()
        painter.setClipRect(row_rect.adjusted(-1, 0, 1, 0))

        x1_view = self._x_view(self.geometry.date_to_x(eff_start))
        x2_view = self._x_view(self.geometry.date_to_x(eff_end + datetime.timedelta(days=1)))

        bar_height = 20
        bar_y = row_rect.y() + (row_rect.height() - bar_height) / 2
        rect = QRectF(x1_view, bar_y, max(4.0, x2_view - x1_view), bar_height)

        # Hover: barra levemente elevada/brilho + contorno
        if is_hovered and not is_selected:
            glow = QRectF(x1_view - 2, bar_y - 2, max(4.0, x2_view - x1_view) + 4, bar_height + 4)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 28))
            painter.drawRoundedRect(glow, 6, 6)

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 4, 4)
        if item.progress > 0:
            prog_w = rect.width() * (item.progress / 100.0)
            painter.setBrush(color.darker(120))
            painter.drawRoundedRect(QRectF(x1_view, bar_y, prog_w, bar_height), 4, 4)

        if is_hovered and not is_selected:
            pen = QPen(QColor(255, 255, 255, 200))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-1.5, -1.5, 1.5, 1.5), 5, 5)

        if is_selected:
            pen = QPen(QColor("#ffffff"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 5, 5)

        painter.restore()

    def _draw_milestone(self, painter: QPainter, item: TimelineItem, row_rect: QRectF, eff_start):
        """Losango na data inicial, repetido todo mês por toda a área VISÍVEL,
        com linha tracejada verde conectando os losangos."""
        color = QColor(SUCCESS_GREEN)  # marco tem cor própria (verde), independente do status
        cy = row_rect.y() + row_rect.height() / 2
        is_selected = (self.selected_item_id == item.id)
        is_hovered = (self._hover_item_id == item.id)

        painter.save()
        painter.setClipRect(row_rect.adjusted(-1, 0, 1, 0))

        # coleta as posições visíveis dos losangos
        positions = []
        d = eff_start
        while True:
            cx = self._x_view(self.geometry.date_to_x(d))
            if cx > row_rect.right() + 20:
                break
            if cx >= row_rect.left() - 20:
                positions.append(cx)
            d = self._add_month(d)

        # linha tracejada SEMPRE visível: percorre toda a área visível a partir da
        # data do marco (alinhada à malha mensal) — não some quando só 1 losango
        # está na tela (ex.: zoom entre dois marcadores)
        line_start = max(row_rect.left(), self._x_view(self.geometry.date_to_x(eff_start)))
        if line_start < row_rect.right():
            pen = QPen(color)
            pen.setWidth(1)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(int(line_start), int(cy), int(row_rect.right()), int(cy))

        for cx in positions:
            size = 9 if (is_selected or is_hovered) else 8
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(45)
            if is_selected or is_hovered:
                painter.setPen(QPen(QColor(255, 255, 255, 200)))
                pen = painter.pen()
                pen.setWidth(2)
                painter.setPen(pen)
            else:
                painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRect(-size, -size, size * 2, size * 2)
            painter.restore()
        painter.restore()

    def _draw_parent_bar(self, painter: QPainter, item: TimelineItem, row_rect: QRectF,
                         eff_start, eff_end):
        x1_view = self._x_view(self.geometry.date_to_x(eff_start))
        x2_view = self._x_view(self.geometry.date_to_x(eff_end + datetime.timedelta(days=1)))
        color = bar_color(item)
        is_selected = (self.selected_item_id == item.id)
        is_hovered = (self._hover_item_id == item.id)

        painter.save()
        painter.setClipRect(row_rect.adjusted(-1, 0, 1, 0))

        # mesma altura/estilo das barras das filhas (20px)
        bar_height = 20
        bar_y = row_rect.y() + (row_rect.height() - bar_height) / 2
        rect = QRectF(x1_view, bar_y, max(4.0, x2_view - x1_view), bar_height)

        if is_hovered and not is_selected:
            glow = rect.adjusted(-2, -2, 2, 2)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 28))
            painter.drawRoundedRect(glow, 6, 6)

        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 4, 4)
        if item.progress > 0:
            prog_w = rect.width() * (item.progress / 100.0)
            painter.setBrush(color.darker(130))
            painter.drawRoundedRect(QRectF(x1_view, bar_y, prog_w, bar_height), 4, 4)

        if is_hovered and not is_selected:
            pen = QPen(QColor(255, 255, 255, 200))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-1.5, -1.5, 1.5, 1.5), 5, 5)
        if is_selected:
            pen = QPen(QColor("#ffffff"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 5, 5)
        painter.restore()

    def _draw_overrun_warning(self, painter: QPainter, row_rect: QRectF, parent_end, children_end):
        """Extensão de AVISO: filhas com prazo além do fim do pai (usuário deve ajustar)."""
        x1 = self._x_view(self.geometry.date_to_x(parent_end + datetime.timedelta(days=1))) + 2
        x2 = self._x_view(self.geometry.date_to_x(children_end + datetime.timedelta(days=1)))
        if x2 <= x1:
            return
        thin_h = 10
        thin_y = row_rect.y() + (row_rect.height() - thin_h) / 2
        rect = QRectF(x1, thin_y, x2 - x1, thin_h)
        warn = QColor(ERROR_RED)
        painter.save()
        painter.setClipRect(row_rect.adjusted(-1, 0, 1, 0))
        # barra hachurada vermelha translúcida
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(warn.red(), warn.green(), warn.blue(), 70))
        painter.drawRoundedRect(rect, 3, 3)
        pen = QPen(warn)
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 3, 3)
        # símbolo de aviso no meio da extensão
        mid = rect.center().x()
        painter.setPen(QColor(ERROR_RED))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(QPointF(mid - 5, thin_y - 2), "⚠")
        painter.restore()

    def _draw_events(self, painter: QPainter, tl_rect: QRectF):
        rows = {}
        for t_item, vrect in self._visible_rows():
            rows[t_item.id] = vrect.center().y()

        for ev in self.events:
            if ev.event_type == "event" and not self.show_events:
                continue
            if ev.event_type == "alarm" and not self.show_alarms:
                continue

            x_view = self._x_view(self.geometry.datetime_to_x(ev.datetime))
            end_x_view = x_view
            if ev.end_datetime and ev.event_type == "event":
                end_x_view = self._x_view(self.geometry.datetime_to_x(ev.end_datetime))
            if x_view < tl_rect.left() - 20 and end_x_view < tl_rect.left() - 20:
                continue
            if x_view > tl_rect.right() + 20 and end_x_view > tl_rect.right() + 20:
                continue

            y = rows.get(ev.task_id)
            if y is None:
                continue

            painter.save()
            # Hover: halo de destaque sob o ícone
            if ev is self._hover_ev:
                painter.setPen(QPen(QColor(255, 255, 255, 200)))
                pen = painter.pen()
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(QColor(255, 255, 255, 30))
                painter.drawEllipse(QPointF(x_view, y), 14, 14)
            if ev.event_type == "alarm":
                painter.setBrush(QColor(WARNING_ORANGE))
                painter.setPen(QColor(0, 0, 0))
                poly = QPolygonF([
                    QPointF(x_view, y - 10),
                    QPointF(x_view - 9, y + 8),
                    QPointF(x_view + 9, y + 8),
                ])
                painter.drawPolygon(poly)
            else:
                event_gray = QColor("#9aa0b6")
                painter.setBrush(event_gray)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(x_view, y), 6, 6)
                if end_x_view > x_view:
                    pen = QPen(event_gray)
                    pen.setWidth(2)
                    painter.setPen(pen)
                    painter.drawLine(QPointF(x_view + 6, y), QPointF(end_x_view - 6, y))
                    painter.drawEllipse(QPointF(end_x_view, y), 6, 6)
            painter.restore()

    def _draw_today_line(self, painter: QPainter, tl_rect: QRectF):
        today_x = self._x_view(self.geometry.datetime_to_x(datetime.datetime.now()))
        if tl_rect.left() <= today_x <= tl_rect.right():
            pen = QPen(QColor(ACCENT_BLUE))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawLine(int(today_x), int(tl_rect.top()), int(today_x), int(tl_rect.bottom()))

    # ---------- hit-test / interação ----------

    def _drag_indicator_text(self):
        """Texto da janeleinha de arraste, conforme o tipo de item arrastado."""
        if self._drag_deadline is not None and self._has_dragged:
            return f"🎯 Prazo Estimado: {self._drag_deadline['cur'].strftime('%d/%m/%Y')}"
        if self._drag_bar is not None and self._has_dragged:
            s = self._drag_bar.get("cur_start") or self._drag_bar["start"]
            e = self._drag_bar.get("cur_end") or self._drag_bar["end"]
            fmt = "%d/%m/%Y"
            mode = self._drag_bar.get("mode", "move")
            if mode == "resize_start":
                return f"⏮ Início: {s.strftime(fmt)}   ·   Fim: {e.strftime(fmt)}"
            if mode == "resize_end":
                return f"⏭ Início: {s.strftime(fmt)}   ·   Fim: {e.strftime(fmt)}"
            return f"📅 {s.strftime(fmt)} → {e.strftime(fmt)}"

        if self._drag_event is not None and self._has_dragged:
            ev = self._drag_event["ev"]
            if self._drag_event.get("snap_day"):
                # alarme "dia todo": só a data muda
                return f"🔔 {ev.datetime.strftime('%d/%m/%Y')} (dia todo)"
            mode = self._drag_event.get("mode", "move")
            fmt_dt = "%d/%m/%Y %H:%M"
            if mode == "resize_start":
                txt = f"⏮ Início: {ev.datetime.strftime(fmt_dt)}"
                if ev.end_datetime:
                    txt += f"   ·   Fim: {ev.end_datetime.strftime(fmt_dt)} (fixo)"
                return txt
            if mode == "resize_end":
                txt = f"⏭ Fim: {ev.end_datetime.strftime(fmt_dt) if ev.end_datetime else '—'}"
                txt += f"   ·   Início: {ev.datetime.strftime(fmt_dt)} (fixo)"
                return txt
            txt = f"{'🔔' if ev.event_type == 'alarm' else '●'} {ev.datetime.strftime(fmt_dt)}"
            if ev.end_datetime:
                txt += f"  →  {ev.end_datetime.strftime(fmt_dt)}"
            return txt
        return None

    def _update_guide(self, pos):
        """Rastreia o mouse na área da timeline para a linha-guia vertical."""
        new_x = pos.x() if pos.x() >= self.timeline_left() else None
        if new_x != self._guide_x:
            self._guide_x = new_x
            self.viewport().update()

    def _datetime_at_x(self, content_x: float) -> datetime.datetime:
        """Data/hora (com fração do dia) na posição de conteúdo x."""
        days = content_x / max(0.0001, self.geometry.pixels_per_day)
        base = datetime.datetime.combine(self.geometry.anchor_date, datetime.time.min)
        return base + datetime.timedelta(days=days)

    def _draw_mouse_guide(self, painter: QPainter, tl_rect: QRectF):
        if self._guide_x is None:
            return
        x = float(self._guide_x)
        if not (tl_rect.left() <= x <= tl_rect.right()):
            return
        painter.save()
        # linha vertical sutil
        pen = QPen(QColor(255, 255, 255, 70))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(int(x), int(tl_rect.top()), int(x), int(tl_rect.bottom()))

        # etiqueta com o dia/hora daquela posição
        dt = self._datetime_at_x(x - tl_rect.left() + self._offset_x)
        txt = dt.strftime("%d/%m/%Y %H:%M")
        painter.setFont(QFont("Segoe UI", 8))
        fm = painter.fontMetrics()
        pad_x, pad_y = 6, 3
        w = fm.horizontalAdvance(txt) + pad_x * 2
        h = fm.height() + pad_y * 2
        bx = min(max(tl_rect.left() + 2, x - w / 2), tl_rect.right() - w - 2)
        by = tl_rect.top() + 2
        rect = QRectF(bx, by, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e1e3a"))
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(QPen(QColor(ACCENT_BLUE)))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(rect, Qt.AlignCenter, txt)
        painter.restore()

    def _draw_deadlines(self, painter: QPainter, tl_rect: QRectF):
        """Marcador 🚩 vermelho do Prazo Estimado na linha da tarefa."""
        for t_item, vrect in self._visible_rows():
            dl = getattr(t_item, 'estimated_deadline', None)
            if not dl:
                continue
            cx = self._x_view(self.geometry.date_to_x(dl))
            if not (tl_rect.left() - 20 <= cx <= tl_rect.right() + 20):
                continue
            cy = vrect.center().y()
            hovered = (self._hover_deadline_id == t_item.id)
            painter.save()
            # halo de hover (mesmo estilo dos eventos)
            if hovered:
                painter.setPen(QPen(QColor(255, 255, 255, 200)))
                pen = painter.pen()
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(QColor(255, 255, 255, 30))
                painter.drawEllipse(QPointF(cx + 2, cy), 14, 14)
            # mastro
            pen = QPen(QColor(ERROR_RED))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(int(cx), int(cy - 11), int(cx), int(cy + 9))
            # bandeira triangular
            painter.setBrush(QColor(ERROR_RED))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(QPolygonF([
                QPointF(cx, cy - 11),
                QPointF(cx + 11, cy - 7),
                QPointF(cx, cy - 3),
            ]))
            painter.restore()

    def _deadline_at(self, pos):
        """Marcador de prazo estimado sob o cursor → (t_item, x) ou (None, None)."""
        for t_item, vrect in self._visible_rows():
            dl = getattr(t_item, 'estimated_deadline', None)
            if not dl:
                continue
            if abs(pos.y() - vrect.center().y()) > vrect.height() / 2:
                continue
            cx = self._x_view(self.geometry.date_to_x(dl))
            if abs(pos.x() - cx) <= 7:
                return t_item, cx
        return None, None

    def _draw_drag_info(self, painter: QPainter):
        if not self._has_dragged or self._drag_pos is None:
            return
        txt = self._drag_indicator_text()
        if not txt:
            return
        painter.save()
        painter.setFont(QFont("Segoe UI", 9))
        fm = painter.fontMetrics()
        pad_x, pad_y = 8, 5
        w = fm.horizontalAdvance(txt) + pad_x * 2
        h = fm.height() + pad_y * 2
        vp = self.viewport().rect()
        x = min(max(4, self._drag_pos.x() + 16), vp.width() - w - 4)
        y = max(4, self._drag_pos.y() - h - 14)
        rect = QRectF(x, y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e1e3a"))
        painter.drawRoundedRect(rect, 5, 5)
        pen = QPen(QColor(ACCENT_BLUE))
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(rect, Qt.AlignCenter, txt)
        painter.restore()

    def _hit_bar(self, pos, t_item):
        """Hit para ARRASTAR: só folhas com datas (pais/marcos não arrastam)."""
        if t_item is None or t_item.is_parent or t_item.is_milestone:
            return False
        return self._hit_range(pos, t_item)

    def _hit_parent_edge(self, pos, t_item):
        """Pai: pontas da própria barra redimensionam o prazo dele (início/fim)."""
        if t_item is None or not t_item.is_parent or t_item.is_milestone:
            return None
        eff_start = t_item.manual_start or t_item.start
        eff_end = t_item.manual_end or t_item.end
        if not (eff_start and eff_end):
            return None
        x1 = self._x_view(self.geometry.date_to_x(eff_start))
        x2 = self._x_view(self.geometry.date_to_x(eff_end + datetime.timedelta(days=1)))
        # zonas delimitadas: só o entorno imediato das pontas (além disso é a faixa de aviso)
        if x1 - 4 <= pos.x() <= x1 + 7:
            return "resize_start"
        if x2 - 7 <= pos.x() <= x2 + 4:
            return "resize_end"
        return None

    def _hit_range(self, pos, t_item):
        """Hit para HOVER/tooltip: qualquer item com período (pai, marco ou folha)."""
        if t_item is None:
            return False
        if t_item.is_parent:
            # pai: usa as DATAS PRÓPRIAS (a barra é dele; estouro das filhas vira aviso)
            eff_start = t_item.manual_start or t_item.start
            eff_end = t_item.manual_end or t_item.end
        else:
            eff_start = t_item.manual_start or t_item.start
            eff_end = t_item.manual_end or t_item.end
        if not (eff_start and eff_end):
            if not (eff_start or eff_end):
                return False
            eff_end = eff_end or eff_start
            eff_start = eff_start or eff_end
        x1 = self._x_view(self.geometry.date_to_x(eff_start))
        x2 = self._x_view(self.geometry.date_to_x(eff_end + datetime.timedelta(days=1)))
        return x1 - 4 <= pos.x() <= x2 + 4

    def _event_at(self, pos):
        rows = {}
        for t_item, vrect in self._visible_rows():
            rows[t_item.id] = vrect.center().y()
        for ev in self.events:
            if ev.event_type == "event" and not self.show_events:
                continue
            if ev.event_type == "alarm" and not self.show_alarms:
                continue
            x_view = self._x_view(self.geometry.datetime_to_x(ev.datetime))
            y = rows.get(ev.task_id)
            if y is None:
                continue
            if (pos.x() - x_view) ** 2 + (pos.y() - y) ** 2 < 144:
                return ev
        return None

    def _event_with_zone(self, pos):
        """Evento sob o cursor + zona (resize_start/resize_end/move).
        Pontas têm prioridade sobre o corpo — permite pegar o fim de eventos longos."""
        rows = {}
        for t_item, vrect in self._visible_rows():
            rows[t_item.id] = vrect.center().y()
        move_candidate = None
        for ev in self.events:
            if ev.event_type == "event" and not self.show_events:
                continue
            if ev.event_type == "alarm" and not self.show_alarms:
                continue
            y = rows.get(ev.task_id)
            if y is None or abs(pos.y() - y) > 14:
                continue
            x_start = self._x_view(self.geometry.datetime_to_x(ev.datetime))
            if ev.end_datetime and ev.end_datetime > ev.datetime:
                x_end = self._x_view(self.geometry.datetime_to_x(ev.end_datetime))
                if abs(pos.x() - x_start) <= 7:
                    return ev, "resize_start"
                if abs(pos.x() - x_end) <= 7:
                    return ev, "resize_end"
                if x_start <= pos.x() <= x_end and move_candidate is None:
                    move_candidate = ev
            else:
                if (pos.x() - x_start) ** 2 + (pos.y() - y) ** 2 < 144 and move_candidate is None:
                    move_candidate = ev
        if move_candidate is not None:
            return move_candidate, "move"
        return None, None

    def _event_edge_zone(self, pos, ev):
        """Zona de resize do evento: 'resize_start'/'resize_end' nas pontas, 'move' no meio/sem duração."""
        if ev is None:
            return None
        rows = {}
        for t_item, vrect in self._visible_rows():
            rows[t_item.id] = vrect.center().y()
        y = rows.get(ev.task_id)
        if y is None or abs(pos.y() - y) > 14:
            return None
        x_start = self._x_view(self.geometry.datetime_to_x(ev.datetime))
        if ev.end_datetime and ev.end_datetime > ev.datetime:
            x_end = self._x_view(self.geometry.datetime_to_x(ev.end_datetime))
            if abs(pos.x() - x_start) <= 7:
                return "resize_start"
            if abs(pos.x() - x_end) <= 7:
                return "resize_end"
            if x_start <= pos.x() <= x_end:
                return "move"
            return None
        # alarme/evento pontual: ícone inteiro move
        if (pos.x() - x_start) ** 2 + (pos.y() - y) ** 2 < 144:
            return "move"
        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        pos = event.position().toPoint()
        if pos.x() < self.timeline_left():
            super().mousePressEvent(event)
            return

        index = self.indexAt(pos)
        t_item = index.sibling(index.row(), 0).data(Qt.UserRole) if index.isValid() else None
        if index.isValid():
            self.setCurrentIndex(index.sibling(index.row(), 0))

        # Alarme/Evento sob o cursor têm prioridade (ícones pequenos, difíceis de acertar)
        ev, ev_mode = self._event_with_zone(pos)
        self._hide_tooltip()
        if ev is not None:
            ev_mode = ev_mode or "move"
            # alarme sem hora específica ("dia todo") arrasta só em dias inteiros
            snap_day = False
            if ev.event_type == "alarm":
                alert_time = str(getattr(ev.raw_entity, "alert_time", "") or "").strip()
                snap_day = not alert_time
            self._drag_event = {
                "ev": ev,
                "start_x": pos.x(),
                "orig_dt": ev.datetime,
                "orig_end": ev.end_datetime,
                "snap_day": snap_day,
                "mode": ev_mode,
            }
            self._has_dragged = False
            self._drag_pos = pos
            self.setCursor(Qt.ClosedHandCursor if ev_mode == "move" else Qt.SizeHorCursor)
            return

        # Prazo Estimado (marcador vermelho): arrastar muda a data (dias inteiros)
        dl_item, _dl_x = self._deadline_at(pos)
        if dl_item is not None:
            self._drag_deadline = {
                "item": dl_item,
                "orig": dl_item.estimated_deadline,
                "cur": dl_item.estimated_deadline,
                "start_x": pos.x(),
            }
            self._has_dragged = False
            self._drag_pos = pos
            self.setCursor(Qt.ClosedHandCursor)
            return

        if t_item and self._hit_bar(pos, t_item):
            eff_start = t_item.manual_start or t_item.start
            eff_end = t_item.manual_end or t_item.end
            # extremos da barra redimensionam só início/fim; meio move a barra inteira
            x1 = self._x_view(self.geometry.date_to_x(eff_start))
            x2 = self._x_view(self.geometry.date_to_x(eff_end + datetime.timedelta(days=1)))
            edge = 7
            if pos.x() <= x1 + edge:
                mode = "resize_start"
                self.setCursor(Qt.SizeHorCursor)
            elif pos.x() >= x2 - edge:
                mode = "resize_end"
                self.setCursor(Qt.SizeHorCursor)
            else:
                mode = "move"
                self.setCursor(Qt.ClosedHandCursor)
            self._drag_bar = {
                "item": t_item,
                "start": eff_start,
                "end": eff_end,
                "start_x": pos.x(),
                "mode": mode,
                "cur_start": eff_start,
                "cur_end": eff_end,
            }
            self._has_dragged = False
            self._drag_pos = pos
            return

        # PAI: pontas da barra dele redimensionam o prazo próprio (sem "move" no meio)
        if t_item and t_item.is_parent:
            edge_mode = self._hit_parent_edge(pos, t_item)
            if edge_mode:
                eff_start = t_item.manual_start or t_item.start
                eff_end = t_item.manual_end or t_item.end
                self._drag_bar = {
                    "item": t_item,
                    "start": eff_start,
                    "end": eff_end,
                    "start_x": pos.x(),
                    "mode": edge_mode,
                    "cur_start": eff_start,
                    "cur_end": eff_end,
                    "is_parent": True,
                }
                self._has_dragged = False
                self._drag_pos = pos
                self.setCursor(Qt.SizeHorCursor)
                return

        self._is_panning = True
        self._pan_start_x = pos.x()
        self._pan_start_offset = self._offset_x
        self._has_dragged = False

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        self._update_guide(pos)

        if self._drag_deadline is not None:
            delta_px = pos.x() - self._drag_deadline["start_x"]
            if abs(delta_px) > 3:
                self._has_dragged = True
            if self._has_dragged:
                delta_days = int(round(delta_px / max(0.0001, self.geometry.pixels_per_day)))
                self._drag_deadline["cur"] = self._drag_deadline["orig"] + datetime.timedelta(days=delta_days)
                self._drag_deadline["item"].estimated_deadline = self._drag_deadline["cur"]
                self._drag_pos = pos
                self.viewport().update()
            return

        if self._drag_event is not None:
            delta_px = pos.x() - self._drag_event["start_x"]
            if abs(delta_px) > 3:
                self._has_dragged = True
            if self._has_dragged:
                info = self._drag_event
                raw_days = delta_px / max(0.0001, self.geometry.pixels_per_day)
                # alarme "dia todo": muda só em dias inteiros (hora nunca altera);
                # com hora específica: arraste livre preservando o horário
                if info.get("snap_day"):
                    delta = datetime.timedelta(days=int(round(raw_days)))
                else:
                    delta = datetime.timedelta(days=raw_days)
                ev = info["ev"]
                mode = info.get("mode", "move")
                if mode == "resize_start":
                    # só o início muda — fim fixo
                    ev.datetime = info["orig_dt"] + delta
                elif mode == "resize_end" and info["orig_end"] is not None:
                    # só o fim muda — início fixo (nunca antes do início)
                    ev.end_datetime = max(info["orig_end"] + delta, ev.datetime)
                else:
                    ev.datetime = info["orig_dt"] + delta
                    if info["orig_end"] is not None:
                        ev.end_datetime = info["orig_end"] + delta
                self._hover_ev = ev
                self._drag_pos = pos
                self.viewport().update()
            return

        if self._drag_bar is not None:
            delta_days = int(round((pos.x() - self._drag_bar["start_x"]) / self.geometry.pixels_per_day))
            if abs(pos.x() - self._drag_bar["start_x"]) > 3:
                self._has_dragged = True
            info = self._drag_bar
            mode = info.get("mode", "move")
            if self._has_dragged:
                if mode == "resize_start" and info["start"]:
                    # só o início muda — nunca passa do fim
                    info["cur_start"] = min(info["start"] + datetime.timedelta(days=delta_days), info["end"])
                elif mode == "resize_end" and info["end"]:
                    # só o fim muda — nunca recua antes do início
                    info["cur_end"] = max(info["end"] + datetime.timedelta(days=delta_days), info["start"])
                else:
                    info["cur_start"] = info["start"] + datetime.timedelta(days=delta_days) if info["start"] else info["start"]
                    info["cur_end"] = info["end"] + datetime.timedelta(days=delta_days) if info["end"] else info["end"]
                # preview na barra (pai usa as datas PRÓPRIAS; folha usa start/end)
                item = info["item"]
                if info.get("is_parent"):
                    item.manual_start = info["cur_start"]
                    item.manual_end = info["cur_end"]
                else:
                    item.start = info["cur_start"]
                    item.end = info["cur_end"]
            info["_delta"] = delta_days if self._has_dragged else 0
            self._drag_pos = pos
            self.viewport().update()
            return

        if self._is_panning:
            delta_x = pos.x() - self._pan_start_x
            if abs(delta_x) > 5:
                self._has_dragged = True
            self.pan_triggered.emit(int(self._pan_start_offset - delta_x))
            return

        # hover + cursor + tooltip sobre a área da timeline
        if pos.x() >= self.timeline_left():
            index = self.indexAt(pos)
            t_item = index.sibling(index.row(), 0).data(Qt.UserRole) if index.isValid() else None

            ev, ev_zone = self._event_with_zone(pos)
            over_bar = bool(t_item and self._hit_range(pos, t_item))

            # marcador de prazo estimado sob o cursor
            dl_item, _dl_x = self._deadline_at(pos)
            new_hover_dl = dl_item.id if dl_item is not None else None
            if new_hover_dl != self._hover_deadline_id:
                self._hover_deadline_id = new_hover_dl
                self.viewport().update()

            if dl_item is not None:
                self.unsetCursor()
                self._show_deadline_tooltip(pos, dl_item)
                super().mouseMoveEvent(event)
                return

            # faixa de AVISO (filhas estouram o prazo do pai) tem tooltip próprio —
            # MAS é a menor prioridade: perde para borda de resize do pai E para
            # qualquer zona de evento/alarme (ex.: ponta de evento sobre a faixa)
            edge_mode_hover = self._hit_parent_edge(pos, t_item) if t_item else None
            over_rect = self._overrun_rect(t_item, index) if t_item else None
            over_warning = bool(
                over_rect and over_rect.adjusted(-4, -8, 4, 8).contains(pos)
                and not edge_mode_hover and ev is None
            )

            # atualiza estado de hover (repinta só quando muda)
            new_hover_id = t_item.id if (t_item and over_bar and ev is None) else None
            if new_hover_id != self._hover_item_id or (ev is None) != (self._hover_ev is None):
                self._hover_item_id = new_hover_id
                self._hover_ev = ev
                self.viewport().update()
            elif ev is not None and ev is not self._hover_ev:
                self._hover_ev = ev
                self.viewport().update()

            if over_warning:
                self.unsetCursor()
                self._show_warning_tooltip(pos, t_item)
                super().mouseMoveEvent(event)
                return

            if t_item and self._hit_bar(pos, t_item):
                # extremos da barra → cursor de redimensionar; meio → mão (mover)
                eff_start = t_item.manual_start or t_item.start
                eff_end = t_item.manual_end or t_item.end
                x1 = self._x_view(self.geometry.date_to_x(eff_start))
                x2 = self._x_view(self.geometry.date_to_x(eff_end + datetime.timedelta(days=1)))
                if pos.x() <= x1 + 7 or pos.x() >= x2 - 7:
                    self.setCursor(Qt.SizeHorCursor)
                else:
                    self.setCursor(Qt.OpenHandCursor)
            elif t_item and self._hit_parent_edge(pos, t_item):
                # pai: pontas da barra dele redimensionam o prazo próprio
                self.setCursor(Qt.SizeHorCursor)
            elif ev is not None and ev_zone in ("resize_start", "resize_end"):
                # pontas do evento com duração → redimensionar início/fim
                self.setCursor(Qt.SizeHorCursor)
            elif ev is not None:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.unsetCursor()

            if ev is not None:
                self._show_event_tooltip(pos, ev)
            elif over_bar:
                self._show_bar_tooltip(pos, t_item)
            else:
                self._hide_tooltip()
        else:
            if self._hover_item_id is not None or self._hover_ev is not None:
                self._hover_item_id = None
                self._hover_ev = None
                self.viewport().update()
            if self._hover_deadline_id is not None:
                self._hover_deadline_id = None
                self.viewport().update()
            self._hide_tooltip()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._guide_x is not None:
            self._guide_x = None
            self.viewport().update()
        if self._hover_deadline_id is not None:
            self._hover_deadline_id = None
            self.viewport().update()
        if self._hover_item_id is not None or self._hover_ev is not None:
            self._hover_item_id = None
            self._hover_ev = None
            self.viewport().update()
        self._hide_tooltip()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return
        pos = event.position().toPoint()
        self.unsetCursor()

        if self._drag_event is not None:
            info = self._drag_event
            self._drag_event = None
            self._drag_pos = None
            ev = info["ev"]
            if self._has_dragged and (
                ev.datetime != info["orig_dt"]
                or (info["orig_end"] is not None and ev.end_datetime != info["orig_end"])
                or (info["orig_end"] is None and ev.end_datetime is not None)
            ):
                # arraste confirmado — host persiste (emite depois de soltar)
                self.viewport().update()
                QTimer.singleShot(0, lambda: self.event_moved.emit(ev, ev.datetime, ev.end_datetime))
            else:
                # clique simples no alarme/evento: NÃO faz nada (editor só no duplo clique/menu)
                self.viewport().update()
            self._has_dragged = False
            return

        if self._drag_deadline is not None:
            info = self._drag_deadline
            self._drag_deadline = None
            self._drag_pos = None
            item = info["item"]
            if self._has_dragged and info["cur"] != info["orig"]:
                item.estimated_deadline = info["cur"]
                self.viewport().update()
                self.deadline_moved.emit(item.id, info["cur"])
            else:
                item.estimated_deadline = info["orig"]
                self.viewport().update()
            self._has_dragged = False
            return

        if self._drag_bar is not None:
            info = dict(self._drag_bar)
            self._drag_bar = None
            self._drag_pos = None
            delta = int(info.get("_delta") or 0)
            item = info["item"]
            is_parent = bool(info.get("is_parent"))
            if self._has_dragged and delta != 0:
                if is_parent:
                    item.manual_start = info["cur_start"]
                    item.manual_end = info["cur_end"]
                else:
                    item.start = info["cur_start"]
                    item.end = info["cur_end"]
                self.viewport().update()
                self.task_moved.emit(item.id, info["cur_start"], info["cur_end"])
            else:
                # sem arraste: reverte preview
                if is_parent:
                    item.manual_start = info["start"]
                    item.manual_end = info["end"]
                else:
                    item.start = info["start"]
                    item.end = info["end"]
                self.viewport().update()
            self._has_dragged = False
            return

        was_panning = self._is_panning
        self._is_panning = False
        if was_panning and not self._has_dragged:
            ev = self._event_at(pos)
            if ev is not None:
                self.event_clicked.emit(ev)
                return
            index = self.indexAt(pos)
            t_item = index.sibling(index.row(), 0).data(Qt.UserRole) if index.isValid() else None
            if t_item:
                self.item_clicked.emit(t_item.id)
        self._has_dragged = False

    def _overrun_rect(self, t_item, index):
        """Rect da faixa de aviso (filhas com prazo além do pai) — None se não houver estouro."""
        if t_item is None or not t_item.is_parent:
            return None
        own_e = t_item.manual_end or t_item.end
        agg_end = t_item.end
        if not own_e or not agg_end or agg_end <= own_e:
            return None
        x1 = self._x_view(self.geometry.date_to_x(own_e + datetime.timedelta(days=1))) + 2
        x2 = self._x_view(self.geometry.date_to_x(agg_end + datetime.timedelta(days=1)))
        tree_item = self.itemFromIndex(index)
        if tree_item is None:
            return None
        vrect = self.visualItemRect(tree_item)
        if vrect.isNull():
            return None
        thin_y = vrect.y() + (vrect.height() - 10) / 2
        return QRectF(x1, thin_y, x2 - x1, 10)

    def _show_warning_tooltip(self, pos, t_item):
        own_e = (t_item.manual_end or t_item.end)
        agg_end = t_item.end
        tooltip = (
            f"<b>⚠ Estouro de prazo</b><br/>"
            f"Uma ou mais subtarefas terminam em <b>{agg_end.strftime('%d/%m/%Y')}</b>, "
            f"depois do prazo deste pai (<b>{own_e.strftime('%d/%m/%Y')}</b>).<br/>"
            f"Ajuste o prazo do pai ou das subtarefas."
        )
        self._tip_text = tooltip
        self._tip_global = self.mapToGlobal(pos)
        self._tip_timer.start()
        QToolTip.showText(self._tip_global, tooltip, self)

    def mouseDoubleClickEvent(self, event):
        pos = event.position().toPoint()
        # prazo estimado → abre a edição da data
        dl_item, _ = self._deadline_at(pos)
        if dl_item is not None:
            self.setCurrentIndex(self.indexAt(pos).sibling(self.indexAt(pos).row(), 0))
            self.edit_deadline_requested.emit(dl_item.raw_task if dl_item.raw_task is not None else dl_item.id)
            return
        # alarme/evento → abre a EDIÇÃO
        ev = self._event_at(pos)
        if ev is not None:
            self.edit_event_requested.emit(ev)
            return
        index = self.indexAt(pos)
        t_item = index.sibling(index.row(), 0).data(Qt.UserRole) if index.isValid() else None
        if t_item:
            self.setCurrentIndex(index.sibling(index.row(), 0))
            self.edit_task_requested.emit(t_item.raw_task if t_item.raw_task is not None else t_item.id)
            return
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        # Ctrl + roda = zoom contínuo (independente dos filtros Dia/Semana/Mês)
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                factor = 1.15 if delta > 0 else 1.0 / 1.15
                new_ppd = max(1.0, min(200.0, self.geometry.pixels_per_day * factor))
                self.ctrl_zoom_requested.emit(float(new_ppd))
            return
        # Shift + roda = rolar a timeline horizontalmente (direita/esquerda)
        if event.modifiers() & Qt.ShiftModifier:
            delta = event.angleDelta().y()
            if delta:
                steps = delta / 120.0
                self.pan_triggered.emit(int(self._offset_x - steps * 3 * self.geometry.pixels_per_day))
            return
        super().wheelEvent(event)

    def contextMenuEvent(self, event):
        pos = event.pos()

        # menu do PRAZO ESTIMADO (marcador vermelho)
        dl_item, _ = self._deadline_at(pos)
        if dl_item is not None:
            idx = self.indexAt(pos)
            if idx.isValid():
                self.setCurrentIndex(idx.sibling(idx.row(), 0))
            menu = QMenu(self)
            act_edit = menu.addAction("✏️ Editar Prazo Estimado")
            act_open = menu.addAction("👁️ Abrir Tarefa")
            menu.addSeparator()
            act_del = menu.addAction("🗑️ Excluir Prazo")
            chosen = menu.exec(event.globalPos())
            task_ref = dl_item.raw_task if dl_item.raw_task is not None else dl_item.id
            if chosen == act_edit:
                self.edit_deadline_requested.emit(task_ref)
            elif chosen == act_open:
                self.open_task_requested.emit(task_ref)
            elif chosen == act_del:
                self.delete_deadline_requested.emit(task_ref)
            return

        # menu próprio para alarmes/eventos
        ev = self._event_at(pos)
        if ev is not None:
            kind = "Alarme" if ev.event_type == "alarm" else "Evento"
            menu = QMenu(self)
            act_edit = menu.addAction(f"✏️ Editar {kind}")
            act_open = menu.addAction("👁️ Abrir Tarefa") if ev.task_id else None
            menu.addSeparator()
            act_del = menu.addAction(f"🗑️ Excluir {kind}")
            chosen = menu.exec(event.globalPos())
            if chosen == act_edit:
                self.edit_event_requested.emit(ev)
            elif act_open is not None and chosen == act_open:
                self.open_task_requested.emit(ev.task_id)
            elif chosen == act_del:
                self.delete_event_requested.emit(ev)
            return

        index = self.indexAt(pos)
        t_item = index.sibling(index.row(), 0).data(Qt.UserRole) if index.isValid() else None
        if not t_item:
            super().contextMenuEvent(event)
            return

        # seleciona a linha sob o cursor antes de abrir o menu
        self.setCurrentIndex(index.sibling(index.row(), 0))

        menu = QMenu(self)
        act_open = menu.addAction("👁️ Abrir Tarefa")
        act_edit = menu.addAction("✏️ Editar Tarefa")
        act_deadline = menu.addAction("🎯 Prazo Estimado")
        menu.addSeparator()
        act_alarm = menu.addAction("🔔 Criar Alarme")
        act_event = menu.addAction("📅 Criar Evento")
        chosen = menu.exec(event.globalPos())
        task_ref = t_item.raw_task if t_item.raw_task is not None else t_item.id
        if chosen == act_open:
            self.open_task_requested.emit(task_ref)
        elif chosen == act_edit:
            self.edit_task_requested.emit(task_ref)
        elif chosen == act_deadline:
            # pré-preenche com a data sob o mouse (se o clique foi na área da timeline)
            if pos.x() >= self.timeline_left():
                mouse_date = self._datetime_at_x(pos.x() - self.timeline_left() + self._offset_x).date()
            else:
                mouse_date = None
            self.edit_deadline_at_requested.emit(task_ref, mouse_date)
        elif chosen == act_alarm:
            self.create_alarm_requested.emit(task_ref)
        elif chosen == act_event:
            self.create_event_requested.emit(task_ref)

    def _refresh_tooltip(self):
        """Reexibe o tooltip enquanto o hover continuar ativo (some só ao tirar o mouse)."""
        if self._tip_text and self._tip_global:
            QToolTip.showText(self._tip_global, self._tip_text, self)

    def _hide_tooltip(self):
        self._tip_text = None
        self._tip_global = None
        self._tip_timer.stop()
        QToolTip.hideText()

    def _show_deadline_tooltip(self, pos, t_item):
        dl = t_item.estimated_deadline
        tooltip = (
            f"<b>🎯 Prazo Estimado</b><br/>"
            f"{t_item.title}<br/>"
            f"Data: <b>{dl.strftime('%d/%m/%Y') if dl else '—'}</b>"
        )
        self._tip_text = tooltip
        self._tip_global = self.mapToGlobal(pos)
        self._tip_timer.start()
        QToolTip.showText(self._tip_global, tooltip, self)

    def _show_event_tooltip(self, pos, ev):
        desc = getattr(ev.raw_entity, 'description', '') or ''
        desc_line = f"<br/>Descrição: {desc}" if desc else ""
        type_name = "Alarme" if ev.event_type == "alarm" else "Evento"
        date_str = ev.datetime.strftime("%d/%m/%Y %H:%M")
        tooltip = f"<b>{type_name}: {ev.title}</b><br/>Horário: {date_str}{desc_line}"
        self._tip_text = tooltip
        self._tip_global = self.mapToGlobal(pos)
        self._tip_timer.start()
        QToolTip.showText(self._tip_global, tooltip, self)

    def _show_bar_tooltip(self, pos, t_item):
        # pai: datas próprias (a barra é dele; estouro das filhas aparece como aviso)
        eff_start = t_item.manual_start or t_item.start
        eff_end = t_item.manual_end or t_item.end
        start_str = eff_start.strftime("%d/%m/%Y") if eff_start else "—"
        end_str = eff_end.strftime("%d/%m/%Y") if eff_end else "—"
        ds = getattr(t_item, 'display_status', t_item.status)
        derived = getattr(t_item, 'derived_status', '')
        extra = f"<br/>Estado: <b>{ds}</b>" if derived else ""
        summ = getattr(t_item, 'summary_text', '')
        summ_line = f"<br/>{summ}" if summ else ""
        kind = "Marco" if t_item.is_milestone else ("Resumo do pai" if t_item.is_parent else "Tarefa")
        tooltip = (
            f"<b>{t_item.title}</b><br/>"
            f"{kind} · Status: {t_item.status}{extra}<br/>"
            f"Período: {start_str} até {end_str}<br/>"
            f"Progresso: {int(t_item.progress)}%{summ_line}"
        )
        self._tip_text = tooltip
        self._tip_global = self.mapToGlobal(pos)
        self._tip_timer.start()
        QToolTip.showText(self._tip_global, tooltip, self)
