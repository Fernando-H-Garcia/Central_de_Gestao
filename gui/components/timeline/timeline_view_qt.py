from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QScrollBar, QPushButton, QTreeWidgetItem)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QBrush, QColor

from gui.components.timeline.timeline_geometry import TimelineGeometry
from gui.components.timeline.timeline_header import TimelineHeader
from gui.components.timeline.gantt_tree_qt import GanttTree
from gui.components.drag_drop_tree_qt import fit_branch_arrows


class TimelineViewQt(QWidget):
    open_task_detail_signal = Signal(int)
    edit_task_signal = Signal(object)   # Task (raw) — abre TaskDialogQt no host
    create_alarm_signal = Signal(object)  # Task (raw) — abre AlarmDialogQt no host
    create_event_signal = Signal(object)  # Task (raw) — abre EventDialogQt no host
    deadline_moved_signal = Signal(int, int, object)   # task_id, deadline_id, nova data
    edit_deadline_signal = Signal(object, object)         # Task (raw) ou id, deadline_id | None
    delete_deadline_signal = Signal(object, object)       # Task (raw) ou id, deadline_id
    edit_deadline_at_signal = Signal(object, object)  # Task (raw) ou id, data sob o mouse | None
    event_clicked = Signal(object)  # TimelineEvent
    event_moved_signal = Signal(object, object, object)  # TimelineEvent, novo início, novo fim
    edit_event_signal = Signal(object)  # TimelineEvent — abre editor no host
    delete_event_signal = Signal(object)  # TimelineEvent — exclui no host
    alarm_clicked = Signal(object)  # compat
    task_moved = Signal(int, object, object)
    # Reordenar linhas arrastando na árvore (task_id, new_parent_id)
    gantt_row_moved = Signal(int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.geometry = TimelineGeometry()
        self._pending_center = True   # recentra em Hoje no primeiro layout real
        self.setup_ui()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # populate roda antes do layout definitivo — recentra quando a largura real chegar
        if self._pending_center and self.isVisible() and self.width() > 100:
            self._pending_center = False
            self.go_to_today()

    def setup_ui(self):
        self.setStyleSheet("background-color: #000000;")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Barra de ferramentas e filtros
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)
        toolbar.setSpacing(6)

        self.btn_today = QPushButton("Ir para Hoje")
        self.btn_today.setObjectName("secondary")
        self.btn_today.clicked.connect(self.go_to_today)
        toolbar.addWidget(self.btn_today)

        toolbar.addSpacing(10)

        # Seletores de Zoom
        self.btn_zoom_day = QPushButton("Dia")
        self.btn_zoom_day.setObjectName("secondary")
        self.btn_zoom_day.clicked.connect(lambda: self.set_zoom("day"))
        toolbar.addWidget(self.btn_zoom_day)

        self.btn_zoom_week = QPushButton("Semana")
        self.btn_zoom_week.setObjectName("secondary")
        self.btn_zoom_week.clicked.connect(lambda: self.set_zoom("week"))
        toolbar.addWidget(self.btn_zoom_week)

        self.btn_zoom_month = QPushButton("Mês")
        self.btn_zoom_month.setObjectName("secondary")
        self.btn_zoom_month.clicked.connect(lambda: self.set_zoom("month"))
        toolbar.addWidget(self.btn_zoom_month)

        toolbar.addSpacing(20)

        # Filtros de visualização
        from PySide6.QtWidgets import QCheckBox
        self.chk_tasks = QCheckBox("Tarefas")
        self.chk_tasks.setChecked(True)
        self.chk_tasks.stateChanged.connect(self._on_filters_changed)
        toolbar.addWidget(self.chk_tasks)

        self.chk_milestones = QCheckBox("Milestones")
        self.chk_milestones.setChecked(True)
        self.chk_milestones.stateChanged.connect(self._on_filters_changed)
        toolbar.addWidget(self.chk_milestones)

        self.chk_events = QCheckBox("Eventos")
        self.chk_events.setChecked(True)
        self.chk_events.stateChanged.connect(self._on_filters_changed)
        toolbar.addWidget(self.chk_events)

        self.chk_alarms = QCheckBox("Alarmes")
        self.chk_alarms.setChecked(True)
        self.chk_alarms.stateChanged.connect(self._on_filters_changed)
        toolbar.addWidget(self.chk_alarms)

        self.chk_completed = QCheckBox("Concluídas")
        self.chk_completed.setChecked(False) # Padrão False para não poluir
        self.chk_completed.stateChanged.connect(self._on_filters_changed)
        toolbar.addWidget(self.chk_completed)

        toolbar.addStretch()
        from PySide6.QtWidgets import QLabel
        legend = QLabel(
            ' \u25b2 <span style="color:#e6a23c;">Alarme</span>  '
            '&nbsp;\u25cf <span style="color:#8b5cf6;">Evento</span>  '
            '&nbsp;\u25c6 <span style="color:#2b8c52;">Marco</span>  '
            '&nbsp;<span style="color:#4a6fe3;">|</span> Hoje'
        )
        legend.setStyleSheet("color: #888; font-size: 11px;")
        legend.setToolTip("Legenda visual da timeline")
        toolbar.addWidget(legend)
        main_layout.addLayout(toolbar)

        # Header de datas (alinhado à coluna da timeline da árvore)
        self.header_widget = TimelineHeader(self.geometry)
        main_layout.addWidget(self.header_widget)

        # Widget ÚNICO: árvore + linha do tempo embutida (sem sincronização)
        self.tree = GanttTree(self.geometry)
        self.tree.open_task_requested.connect(self._emit_open_task)
        self.tree.edit_task_requested.connect(self.edit_task_signal.emit)
        self.tree.create_alarm_requested.connect(self.create_alarm_signal.emit)
        self.tree.create_event_requested.connect(self.create_event_signal.emit)
        self.tree.deadline_moved.connect(self.deadline_moved_signal.emit)
        self.tree.edit_deadline_requested.connect(self.edit_deadline_signal.emit)
        self.tree.delete_deadline_requested.connect(self.delete_deadline_signal.emit)
        self.tree.edit_deadline_at_requested.connect(self.edit_deadline_at_signal.emit)
        self.tree.item_clicked.connect(self._on_tree_item_clicked)
        self.tree.event_clicked.connect(self._on_tree_event_clicked)
        self.tree.event_moved.connect(self.event_moved_signal.emit)
        self.tree.edit_event_requested.connect(self.edit_event_signal.emit)
        self.tree.delete_event_requested.connect(self.delete_event_signal.emit)
        self.tree.task_moved.connect(self.task_moved.emit)
        self.tree.item_moved.connect(self.gantt_row_moved.emit)
        self.tree.pan_triggered.connect(self._on_pan_triggered)
        self.tree.ctrl_zoom_requested.connect(self._on_ctrl_zoom)
        main_layout.addWidget(self.tree, 1)

        # Scrollbar horizontal customizada (controla offset_x da árvore e do header)
        self.h_scrollbar = QScrollBar(Qt.Horizontal)
        self.h_scrollbar.setMinimum(0)
        self.h_scrollbar.setMaximum(10000) # Será atualizado depois
        self.h_scrollbar.valueChanged.connect(self._on_h_scroll)
        main_layout.addWidget(self.h_scrollbar)

    def _sync_header_margin(self):
        margin = self.tree.timeline_left() + 1
        self.header_widget.set_left_margin(margin)

    def _on_h_scroll(self, value):
        self.header_widget.set_offset_x(value)
        self.tree.set_offset_x(value)

    def _on_pan_triggered(self, new_offset):
        val = max(self.h_scrollbar.minimum(), min(new_offset, self.h_scrollbar.maximum()))
        self.h_scrollbar.setValue(val)

    def _emit_open_task(self, task_or_id):
        if hasattr(task_or_id, "id"):
            self.open_task_detail_signal.emit(int(task_or_id.id))
        else:
            self.open_task_detail_signal.emit(int(task_or_id))

    def _on_tree_item_clicked(self, task_id):
        # clique na barra já seleciona a linha nativamente (widget único)
        pass

    def _on_tree_event_clicked(self, ev):
        # Encaminha para o host (project_360_qt) abrir diálogo de detalhe
        self.event_clicked.emit(ev)
        if ev.event_type == "alarm":
            self.alarm_clicked.emit(ev)

    def _on_filters_changed(self):
        self._update_visible_items()

    def set_zoom(self, mode: str):
        if mode == "day":
            self.geometry.set_scale(50.0) # Zoom maior
        elif mode == "week":
            self.geometry.set_scale(15.0) # Zoom intermediário
        elif mode == "month":
            self.geometry.set_scale(5.0)  # Zoom menor para caber mais meses

        self.header_widget.update()
        self.tree.viewport().update()
        self.update_h_scrollbar()
        self.go_to_today()

    def _on_ctrl_zoom(self, new_ppd: float):
        """Zoom contínuo (Ctrl+roda): mantém a data do centro visível ancorada."""
        import datetime
        tl_left = self.tree.timeline_left()
        vp_w = self.tree.viewport().width()
        rel = max(0.0, (vp_w - tl_left) / 2.0)
        # data atualmente no centro da área da timeline
        anchor_date = self.geometry.x_to_date(self.h_scrollbar.value() + rel)

        self.geometry.set_scale(new_ppd)
        new_offset = int(max(0.0, min(
            self.geometry.date_to_x(anchor_date) - rel,
            1825 * self.geometry.pixels_per_day,
        )))

        self.header_widget.update()
        self.update_h_scrollbar()
        self.tree.viewport().update()
        self.h_scrollbar.setValue(new_offset)

    def _update_visible_items(self):
        """Aplica filtros escondendo linhas — barras/eventos somem junto (widget único)."""
        show_completed = self.chk_completed.isChecked()
        show_tasks = self.chk_tasks.isChecked()
        show_milestones = self.chk_milestones.isChecked()

        def set_hidden_recursive(node):
            for i in range(node.childCount()):
                child = node.child(i)
                ct = child.data(0, Qt.UserRole)
                if ct:
                    is_c = ct.status == "Concluído"
                    mc = show_completed or not is_c
                    mt = (show_milestones if ct.is_milestone else show_tasks)
                    child.setHidden(not (mc and mt))
                else:
                    child.setHidden(False)
                set_hidden_recursive(child)

        self.tree.setUpdatesEnabled(False)
        try:
            set_hidden_recursive(self.tree.invisibleRootItem())
        finally:
            self.tree.setUpdatesEnabled(True)
        self.tree.show_events = self.chk_events.isChecked()
        self.tree.show_alarms = self.chk_alarms.isChecked()
        self.tree.viewport().update()

    def populate(self, timeline_items):
        self.tree.clear()

        def create_tree_item(t_item, parent_widget, depth=0):
            item = QTreeWidgetItem(parent_widget)
            item.setData(0, Qt.UserRole, t_item)
            item.setSizeHint(0, QSize(0, self.geometry.row_height)) # Força altura da linha

            prefix = ""
            if depth > 0:
                prefix = ("    " * (depth - 1)) + "└─ "
            item.setText(0, prefix + t_item.title)

            # Cores por profundidade
            if depth > 0:
                title_color = "#b06ab3" if depth >= 2 else "#e67e22"
                item.setForeground(0, QBrush(QColor(title_color)))
                bg = QColor(255, 255, 255, 0)
                if depth == 1:
                    bg = QColor(230, 126, 34, 18)
                elif depth >= 2:
                    bg = QColor(176, 106, 179, 22)
                item.setBackground(0, QBrush(bg))

            for child_t_item in t_item.children:
                create_tree_item(child_t_item, item, depth + 1)

            item.setExpanded(True)
            return item

        for t_item in timeline_items:
            create_tree_item(t_item, self.tree, 0)

        fit_branch_arrows(self.tree)
        self._sync_header_margin()
        self._update_visible_items()

        # Ajustar tamanho do scroll horizontal baseado nas datas
        self.update_h_scrollbar()
        self.go_to_today()

    def set_events(self, events):
        self.tree.set_events(events)

    def update_h_scrollbar(self):
        # Âncora em hoje−730 dias (ver timeline_geometry); cobrir até hoje+1095 dias
        # => total 1825 dias de rolagem (2 anos de passado + 3 de futuro)
        max_pixels = 1825 * self.geometry.pixels_per_day
        self.h_scrollbar.setMaximum(int(max_pixels))

    def go_to_today(self):
        import datetime
        today_x = self.geometry.datetime_to_x(datetime.datetime.now())
        tl_width = max(100, self.tree.viewport().width() - self.tree.timeline_left())
        # Hoje NÃO fica no centro: entra com ~1 mês de "passado visível" à esquerda
        # (limitado a 40% da área visível para caber em qualquer zoom)
        lead_px = min(30 * self.geometry.pixels_per_day, tl_width * 0.4)
        target_x = int(today_x - lead_px)
        target_x = max(0, min(target_x, self.h_scrollbar.maximum()))
        self.h_scrollbar.setValue(target_x)
