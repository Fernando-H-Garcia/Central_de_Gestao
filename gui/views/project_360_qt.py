from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QAbstractItemView, QMenu, QTreeWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QColor, QBrush, QFont

from gui.components.drag_drop_tree_qt import DragDropTreeWidget, SortableTreeWidgetItem
from services.project_service import ProjectService
from gui.theme import get_status_color, get_energy_color, format_colored_label, format_status, get_archived_color
from services.task_service import TaskService
from services.event_service import EventService
from services.alert_service import AlertService
from core.event_bus import event_bus

STATUS_SORT_ORDER = {
    "Pendente": 1,
    "Backlog": 1,
    "Em Andamento": 3,
    "Pausado": 4,
    "Aguardando": 5,
    "Bloqueado": 6,
    "Concluído": 7
}

ENERGY_SORT_ORDER = {
    "Baixa": 1,
    "Média": 2,
    "Alta": 3,
    "Máxima": 4,
    "Crítica": 4
}

class Project360Qt(QWidget):
    # Signal emitted when user wants to go back to the Projects list
    go_back = Signal()
    open_task_detail_signal = Signal(int)

    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        
        self.project_service = ProjectService()
        self.task_service = TaskService()
        self.event_service = EventService()
        self.alert_service = AlertService()
        
        self.show_archived_tasks = False
        self.settings = QSettings("Solinftec", "CentralGestao")
        self._alarm_popup_open = False
        
        self.setup_ui()
        self.load_data()
        self.restore_sort_order()
        
        # Alarme agora é disparado globalmente no MainWindow (_check_global_alarms),
        # independente de qual tela está visível. Nada é agendado aqui para
        # evitar duplo-popup (Project360 + global).
        self._alarm_popup_open = False
        self._alarm_stuck_since = None
        
        event_bus.subscribe("snapshot_updated", self.safe_load_data)
        event_bus.subscribe("entity_updated", self.safe_load_data)
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self):
        event_bus.unsubscribe("snapshot_updated", self.safe_load_data)
        event_bus.unsubscribe("entity_updated", self.safe_load_data)

    def safe_load_data(self, _=None):
        try:
            self.load_data()
        except RuntimeError:
            pass

    def _check_alarms_periodically(self):
        """Verifica se há novos alarmes no horário sem bloquear se já há popup aberto."""
        if not self.isVisible():
            return
        if self._alarm_popup_open:
            # Anti-stuck: se ficou True por mais de 60s, força reset
            if self._alarm_stuck_since is None:
                self._alarm_stuck_since = __import__('time').time()
            elif __import__('time').time() - self._alarm_stuck_since > 60:
                self._alarm_popup_open = False
                self._alarm_stuck_since = None
            return
        self._alarm_stuck_since = None
        self._check_and_show_alarms()

    def _check_and_show_alarms(self):
        """Verifica alarmes ativos das tarefas deste projeto e exibe o popup se houver."""
        if self._alarm_popup_open:
            return
        try:
            self._alarm_popup_open = True
            # Marca como atrasados os alertas que já passaram do prazo
            self.alert_service.mark_overdue_alerts()
            
            alarms = self.alert_service.get_active_alarms_for_project(
                self.project_id, self.task_service
            )
            if not alarms:
                return

            # Buscar tarefas para montar mapa id → title
            tasks = self.task_service.get_tasks_by_project(self.project_id)
            task_map = {t.id: t for t in tasks}

            # Injetar _task_title em cada alarme para o popup usar
            for alarm in alarms:
                t = task_map.get(alarm.entity_id)
                alarm._task_title = t.title if t else f"Tarefa #{alarm.entity_id}"

            from gui.dialogs_qt.alarm_popup_qt import AlarmPopupQt
            popup = AlarmPopupQt(alarms, task_map, parent=self)
            popup.open_task_requested.connect(self.open_task_detail_signal.emit)
            popup.exec()
            self.load_data()
        except Exception:
            import traceback, os
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN _check_and_show_alarms:\n")
                    traceback.print_exc(file=f)
            except:
                pass
        finally:
            self._alarm_popup_open = False
            self._alarm_stuck_since = None

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 🔝 Top Header 🔝
        header_layout = QHBoxLayout()
        
        self.btn_back = QPushButton("← Voltar")
        self.btn_back.setObjectName("secondary")
        self.btn_back.clicked.connect(self._on_back_clicked)
        header_layout.addWidget(self.btn_back)
        
        self.lbl_title = QLabel("Visão 360°")
        self.lbl_title.setObjectName("header")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.lbl_title, stretch=1)
        
        self.btn_edit = QPushButton("✏️ Editar Projeto")
        self.btn_edit.setObjectName("secondary")
        self.btn_edit.clicked.connect(self.edit_project)
        header_layout.addWidget(self.btn_edit)

        header_layout.addSpacing(20)
        from gui.components.references_panel_qt import ReferencesPanelQt
        self.refs_panel = ReferencesPanelQt(entity_type="project", entity_id=self.project_id, parent=self)
        header_layout.addWidget(self.refs_panel)

        main_layout.addLayout(header_layout)
        
        # ── Overview Card ──
        overview_layout = QVBoxLayout()
        self.lbl_obj = QLabel("Objetivo: —")
        overview_layout.addWidget(self.lbl_obj)
        
        stats_layout = QHBoxLayout()
        self.lbl_status = QLabel("Status: —")
        self.lbl_prio = QLabel("Prioridade: —")
        self.lbl_due = QLabel("Prazo: —")
        stats_layout.addWidget(self.lbl_status)
        stats_layout.addWidget(self.lbl_prio)
        stats_layout.addWidget(self.lbl_due)
        stats_layout.addStretch()
        overview_layout.addLayout(stats_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2a2a3f;
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #2563EB;
                border-radius: 5px;
            }
        """)
        overview_layout.addWidget(self.progress_bar)
        
        main_layout.addLayout(overview_layout)
        
        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2a2a3f; }
            QTabBar::tab {
                background: #1c1c2e;
                color: #888;
                padding: 10px 20px;
                border: 1px solid #2a2a3f;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #2a2a3f;
                color: #fff;
                font-weight: bold;
            }
        """)
        
        # Tarefas Tab
        self.tab_tasks = QWidget()
        self.setup_tasks_tab()
        self.tabs.addTab(self.tab_tasks, "Tarefas")
        
        # Planejamento Tab
        from gui.components.timeline.timeline_view_qt import TimelineViewQt
        self.tab_timeline = TimelineViewQt(parent=self)
        self.tab_timeline.open_task_detail_signal.connect(self.open_task_detail_signal.emit)
        self.tab_timeline.edit_task_signal.connect(self._edit_task_from_timeline)
        self.tab_timeline.create_alarm_signal.connect(self._create_alarm_from_timeline)
        self.tab_timeline.create_event_signal.connect(self._create_event_from_timeline)
        self.tab_timeline.event_clicked.connect(self._on_timeline_event_clicked)
        self.tab_timeline.event_moved_signal.connect(self._on_timeline_event_moved)
        self.tab_timeline.edit_event_signal.connect(self._on_timeline_edit_event)
        self.tab_timeline.delete_event_signal.connect(self._delete_timeline_event)
        self.tab_timeline.task_moved.connect(self._on_timeline_task_moved)
        self.tabs.addTab(self.tab_timeline, "Planejamento")
        
        # Ideias Tab
        from gui.views.ideas_qt import IdeasQt
        self.tab_ideas = IdeasQt(project_id=self.project_id)
        self.tabs.addTab(self.tab_ideas, "Ideias")
        
        # Alarmes e Eventos no nível das abas principais (aba Agenda removida)
        self.setup_agenda_tabs()
        
        main_layout.addWidget(self.tabs, stretch=1)
        self._init_tab_navigation()

    def setup_tasks_tab(self):
        layout = QVBoxLayout(self.tab_tasks)
        
        self.metrics_layout = QHBoxLayout()
        layout.addLayout(self.metrics_layout)
        
        self.active_status_filter = None
        self.metric_cards = {}
        
        from gui.components.metric_card_qt import MetricCardQt
        
        for icon, title, color in [("📋", "Tarefas", "#ffffff"), 
                                   ("⚠️", "Atrasadas", "#e53935"),
                                   ("⏳", "Em andamento", get_status_color('Em Andamento')),
                                   ("🔄", "Aguardando", get_status_color('Aguardando')),
                                   ("📌", "Pendente", get_status_color('Pendente')),
                                   ("🚫", "Bloqueadas", get_status_color('Bloqueado')),
                                   ("⏸️", "Pausadas", get_status_color('Pausado')),
                                   ("✅", "Concluídas", get_status_color('Concluído'))]:
            card = MetricCardQt(title, 0, color, icon=icon)
            card.clicked.connect(self.on_metric_clicked)
            self.metric_cards[title] = card
            self.metrics_layout.addWidget(card)
        
        self.metric_cards["Tarefas"].set_active(True)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_archived_tasks = QPushButton("📦 Arquivados: OFF")
        self.btn_archived_tasks.setObjectName("secondary")
        self.btn_archived_tasks.setCheckable(True)
        self.btn_archived_tasks.clicked.connect(self.toggle_archived_tasks)
        btn_layout.addWidget(self.btn_archived_tasks)
        
        btn_new_task = QPushButton("📋 + Nova Tarefa")
        btn_new_task.setObjectName("secondary")
        btn_new_task.clicked.connect(self.new_task)
        btn_layout.addWidget(btn_new_task)
        layout.addLayout(btn_layout)
        
        self.tbl_tasks = DragDropTreeWidget()
        self.tbl_tasks.setColumnCount(6)
        self.tbl_tasks.setHeaderLabels(["ID", "Título", "Status", "Prioridade", "Período", "Progresso"])
        self.tbl_tasks.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_tasks.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_tasks.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_tasks.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_tasks.header().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tbl_tasks.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_tasks.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_tasks.setSortingEnabled(False)
        self.tbl_tasks.setAlternatingRowColors(True)
        self.tbl_tasks.itemDoubleClicked.connect(self.open_task_detail)
        self.tbl_tasks.itemExpanded.connect(self._on_item_expanded)

        from gui.components.badge_delegate import BadgeDelegate
        from gui.components.progress_bar_delegate import ProgressBarDelegate
        self.tbl_tasks.setItemDelegateForColumn(2, BadgeDelegate("status", parent=self.tbl_tasks))
        self.tbl_tasks.setItemDelegateForColumn(3, BadgeDelegate("priority", parent=self.tbl_tasks))
        self.tbl_tasks.setItemDelegateForColumn(5, ProgressBarDelegate(parent=self.tbl_tasks))
        
        self.tbl_tasks.item_moved.connect(self.handle_row_moved)
        self.tbl_tasks.header().sectionClicked.connect(self.handle_header_click)
        
        # Context menu
        self.tbl_tasks.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_tasks.customContextMenuRequested.connect(self.show_task_context_menu)
        
        layout.addWidget(self.tbl_tasks)

    def _on_item_expanded(self, item):
        def _expand_subtree(it):
            for i in range(it.childCount()):
                ch = it.child(i)
                ch.setExpanded(True)
                _expand_subtree(ch)
        _expand_subtree(item)

    def open_task_detail(self, item, column):
        task_id_str = item.text(0)
        if not task_id_str: return
        task_id = int(task_id_str)
        self.open_task_detail_signal.emit(task_id)

    # ── Navegação de abas como sub-janelas (Voltar volta entre abas) ──
    def _init_tab_navigation(self):
        """Registra mudanças de aba principal numa pilha de posições.
        O Voltar consome essa pilha primeiro; esgotada, emite go_back
        (volta para a janela anterior)."""
        self._pos_history = []           # lista de índices de aba principal
        self._suppress_tab_nav = False   # ignora mudanças programáticas
        self._cur_main_idx = self.tabs.currentIndex()
        self.tabs.currentChanged.connect(self._on_main_tab_changed)

    def _push_pos(self, main_idx):
        if main_idx is None:
            main_idx = self._cur_main_idx
        # Evita historico duplicado se a posicao ja for a corrente
        if self._pos_history and self._pos_history[-1] == main_idx:
            return
        if self._pos_history and self._pos_history[-1] == self._cur_main_idx:
            return
        self._pos_history.append(main_idx)

    def _on_main_tab_changed(self, new_idx):
        if self._suppress_tab_nav:
            return
        if new_idx == self._cur_main_idx:
            return
        self._push_pos(self._cur_main_idx)
        self._cur_main_idx = new_idx

    def _on_back_clicked(self):
        """Voltar dentro das abas primeiro; depois window back."""
        while self._pos_history:
            idx = self._pos_history.pop()
            if idx == self._cur_main_idx:
                continue
            self._suppress_tab_nav = True
            self.tabs.setCurrentIndex(idx)
            self._cur_main_idx = self.tabs.currentIndex()
            self._suppress_tab_nav = False
            return
        self.go_back.emit()

    def setup_agenda_tabs(self):
        # Aba Alarmes
        tab_alarmes = QWidget()
        layout_alarmes = QVBoxLayout(tab_alarmes)
        from gui.components.alarm_cards_qt import AlarmCardsWidget
        self.tree_alarms = AlarmCardsWidget(grouping="date", filter_project_id=self.project_id, main_window=self.window(), parent=self)
        layout_alarmes.addWidget(self.tree_alarms)
        self.tabs.addTab(tab_alarmes, "Alarmes")

        # Aba Eventos
        tab_eventos = QWidget()
        layout_eventos = QVBoxLayout(tab_eventos)
        
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        self.btn_new_event = QPushButton("📅 + Novo Evento")
        self.btn_new_event.setObjectName("primary")
        self.btn_new_event.clicked.connect(self.new_agenda_event)
        header_layout.addWidget(self.btn_new_event)
        layout_eventos.addLayout(header_layout)
        
        from gui.components.agenda_tree_qt import AgendaTreeWidget
        self.tree_agenda = AgendaTreeWidget(grouping="date", filter_project_id=self.project_id, main_window=self.window(), parent=self)
        layout_eventos.addWidget(self.tree_agenda)
        self.tabs.addTab(tab_eventos, "Eventos")
        


    def toggle_archived_tasks(self):
        self.show_archived_tasks = self.btn_archived_tasks.isChecked()
        self.btn_archived_tasks.setText(f"📦 Arquivados: {'ON' if self.show_archived_tasks else 'OFF'}")
        self.load_data()

    def on_metric_clicked(self, title):
        self.active_status_filter = title if title != "Tarefas" else None
        for t, card in self.metric_cards.items():
            card.set_active(t == title)
        self.load_data()

    def load_data(self):
        print(f"[DEBUG] load_data() called, project_id={getattr(self, 'project_id', None)}")
        self.project = self.project_service.project_repo.get_by_id(self.project_id)
        if not self.project:
            print(f"[DEBUG] load_data: no project found for id={self.project_id}")
            return
        print(f"[DEBUG] load_data: project={self.project.name}, id={self.project.id}")
            
        self.lbl_title.setText(f"Projeto: {self.project.name}")
        self.lbl_obj.setText(f"Objetivo: {self.project.objective or '—'}")
        archived = getattr(self.project, 'is_archived', False)
        proj_status = format_status(self.project.status, archived)
        proj_color = get_archived_color() if archived else get_status_color(self.project.status)
        self.lbl_status.setText(f'Status: <span style="color: {proj_color}; font-weight: bold;">{proj_status}</span>')
        self.lbl_prio.setText(format_colored_label("Prioridade:", self.project.priority, get_energy_color))
        due = "-"
        if self.project.due_date:
            try:
                import datetime
                dt = datetime.datetime.fromisoformat(str(self.project.due_date))
                due = dt.strftime("%d/%m/%Y")
                
                # Calculate days remaining
                today = datetime.datetime.now().date()
                delta = (dt.date() - today).days
                if delta < 0:
                    due += f" ({abs(delta)} dias atrasado)"
                elif delta == 0:
                    due += " (Hoje)"
                else:
                    due += f" ({delta} dias)"
            except:
                due = str(self.project.due_date).split()[0]
                
        self.lbl_due.setText(f"Prazo: {due}")
        
        # Progress math (simplified)
        tasks = self.task_service.get_tasks_by_project(self.project_id)
        if self.show_archived_tasks:
            tasks = [t for t in self.task_service.get_all_archived() if t.project_id == self.project_id]
            
        total = len(tasks)
        concluidas = sum(1 for t in tasks if t.status == 'Concluído')
        pct = int((concluidas / total * 100) if total > 0 else 0)
        self.progress_bar.setValue(pct)
        self.progress_bar.setFormat(f"{pct}% ({concluidas}/{total} Tarefas Concluídas)")
        
        em_andamento = sum(1 for t in tasks if t.status == 'Em Andamento')
        aguardando = sum(1 for t in tasks if t.status == 'Aguardando')
        pendente = sum(1 for t in tasks if t.status in ('Pendente', 'Backlog'))
        bloqueadas = sum(1 for t in tasks if t.status == 'Bloqueado')
        pausadas = sum(1 for t in tasks if t.status == 'Pausado')
        
        import datetime
        hoje_str = datetime.datetime.now().strftime("%Y-%m-%d")
        atrasadas = sum(1 for t in tasks if t.due_date and t.due_date < hoje_str and t.status != 'Concluído')

        self.metric_cards["Tarefas"].update_count(total)
        self.metric_cards["Concluídas"].update_count(concluidas)
        self.metric_cards["Em andamento"].update_count(em_andamento)
        self.metric_cards["Aguardando"].update_count(aguardando)
        self.metric_cards["Pendente"].update_count(pendente)
        self.metric_cards["Bloqueadas"].update_count(bloqueadas)
        self.metric_cards["Pausadas"].update_count(pausadas)
        self.metric_cards["Atrasadas"].update_count(atrasadas)
        
        # Filtrar o que vai ser exibido na tabela se o filtro estiver ativo
        project_tasks = tasks
        if self.active_status_filter:
            if self.active_status_filter == "Concluídas":
                project_tasks = [t for t in project_tasks if t.status == 'Concluído']
            elif self.active_status_filter == "Em andamento":
                project_tasks = [t for t in project_tasks if t.status == 'Em Andamento']
            elif self.active_status_filter == "Aguardando":
                project_tasks = [t for t in project_tasks if t.status == 'Aguardando']
            elif self.active_status_filter == "Pendente":
                project_tasks = [t for t in project_tasks if t.status in ('Pendente', 'Backlog')]
            elif self.active_status_filter == "Bloqueadas":
                project_tasks = [t for t in project_tasks if t.status == 'Bloqueado']
            elif self.active_status_filter == "Pausadas":
                project_tasks = [t for t in project_tasks if t.status == 'Pausado']
            elif self.active_status_filter == "Atrasadas":
                project_tasks = [t for t in project_tasks if t.due_date and t.due_date < hoje_str and t.status != 'Concluído']
            
        self.current_tasks = project_tasks

        self.refs_panel.set_entity("project", self.project_id)

        # If no specific filter is active, exclude "Concluído" from the default view
        if not self.active_status_filter:
            project_tasks = [t for t in project_tasks if t.status != 'Concluído']
        
        self.tbl_tasks.setSortingEnabled(False)
        project_tasks = sorted(project_tasks, key=lambda t: t.position if t.position is not None else 0.0)
        
        # ADR-005 workaround: remove delegates AND freeze updates during entire population
        # to avoid Qt 6.6.x paint crash on QTreeWidget with BadgeDelegate
        old_delegates = {}
        for col in (2, 3, 5):
            old_delegates[col] = self.tbl_tasks.itemDelegateForColumn(col)
            self.tbl_tasks.setItemDelegateForColumn(col, None)
        
        self.tbl_tasks.setUpdatesEnabled(False)
        try:
            print(f"[DEBUG] load_data: populating {len(project_tasks)} tasks into tree")
            self.tbl_tasks.clear()
            
            main_tasks = [t for t in project_tasks if not getattr(t, 'parent_task_id', None)]
            subtasks_by_parent = {}
            for t in project_tasks:
                pid = getattr(t, 'parent_task_id', None)
                if pid is not None:
                    subtasks_by_parent.setdefault(pid, []).append(t)

            # Promover órfãs ao nível raiz: subtarefas cuja tarefa-pai não está visível (ex.: pai filtrado por status)
            visible_ids = {t.id for t in project_tasks}
            orphan_ids = []
            for t in project_tasks:
                pid = getattr(t, 'parent_task_id', None)
                if pid is not None and pid not in visible_ids:
                    orphan_ids.append(t.id)
            if orphan_ids:
                main_tasks += [t for t in project_tasks if t.id in orphan_ids]

            def compute_progress(t):
                subs = subtasks_by_parent.get(t.id, [])
                if not subs:
                    return None
                total = len(subs)
                done = sum(1 for s in subs if s.status == 'Concluído')
                return f"{done}/{total}"

            def create_tree_item(t, parent_item, depth=0):
                item = SortableTreeWidgetItem(parent_item)
                item.setData(0, Qt.UserRole, t)
                item.setText(0, str(t.id))
                item.setTextAlignment(0, Qt.AlignCenter)
                prefix = ""
                if depth > 0:
                    prefix = ("    " * (depth - 1)) + "└─ "
                item.setText(1, prefix + t.title)

                # Indicador visual de profundidade: cor do título + leve background
                if depth > 0:
                    title_color = "#b06ab3" if depth >= 2 else "#e67e22"
                    item.setForeground(1, QBrush(QColor(title_color)))
                    from PySide6.QtGui import QColor as _QC
                    bg = _QC(255, 255, 255, 0)
                    if depth == 1:
                        bg = _QC(230, 126, 34, 18)
                    elif depth >= 2:
                        bg = _QC(176, 106, 179, 22)
                    for _c in range(self.tbl_tasks.columnCount()):
                        item.setBackground(_c, QBrush(bg))

                item.setText(2, format_status(t.status, getattr(t, 'is_archived', False)))
                item.setTextAlignment(2, Qt.AlignCenter)
                item.setText(3, t.energy_level)
                item.setTextAlignment(3, Qt.AlignCenter)
                
                period_str = ""
                start_str = ""
                due_str = ""
                if hasattr(t, 'start_date') and t.start_date:
                    try:
                        import datetime
                        start_dt = datetime.datetime.fromisoformat(str(t.start_date))
                        start_str = start_dt.strftime("%d/%m/%Y")
                    except:
                        start_str = str(t.start_date).split()[0]
                        
                if t.due_date:
                    try:
                        import datetime
                        dt = datetime.datetime.fromisoformat(str(t.due_date))
                        due_str = dt.strftime("%d/%m/%Y")
                        if t.status != 'Concluído':
                            today = datetime.datetime.now().date()
                            delta = (dt.date() - today).days
                            if delta < 0: due_str += f" ({abs(delta)} dias atrasado)"
                            elif delta == 0: due_str += " (Hoje)"
                            else: due_str += f" ({delta} dias)"
                    except:
                        due_str = str(t.due_date).split()[0]
                
                if start_str and due_str: period_str = f"{start_str} - {due_str}"
                elif start_str: period_str = f"A partir de {start_str}"
                elif due_str: period_str = f"Até {due_str}"
                else: period_str = "-"
                
                item.setText(4, period_str)
                item.setTextAlignment(4, Qt.AlignCenter)
                item.sort_values = {4: t.due_date or ""}

                progress_str = compute_progress(t)
                if progress_str:
                    item.setText(5, progress_str)
                    try:
                        done = int(progress_str.split("/")[0])
                        total = int(progress_str.split("/")[1])
                        item.sort_values[5] = done / total if total else 0.0
                    except (ValueError, IndexError):
                        pass
                else:
                    item.setText(5, "")
                item.setTextAlignment(5, Qt.AlignCenter)
                
                for sub_t in subtasks_by_parent.get(t.id, []):
                    create_tree_item(sub_t, item, depth + 1)
                
                return item

            for t in main_tasks:
                create_tree_item(t, self.tbl_tasks, 0)
                
        finally:
            # Restore updates and delegates BEFORE expandAll to prevent paint crash
            for col, delg in old_delegates.items():
                self.tbl_tasks.setItemDelegateForColumn(col, delg)
            self.tbl_tasks.setUpdatesEnabled(True)
            
        from gui.components.drag_drop_tree_qt import fit_branch_arrows
        fit_branch_arrows(self.tbl_tasks)
        self.tbl_tasks.expandAll()
        self.restore_sort_order()
            
        # Popula a aba Planejamento (Timeline) — usa todas as tarefas (inclui Concluídas, filtro fica no checkbox)
        try:
            from gui.components.timeline.timeline_mapper import TimelineMapper
            tl_main = [t for t in tasks if not getattr(t, 'parent_task_id', None)]
            tl_by_parent = {}
            for t in tasks:
                pid = getattr(t, 'parent_task_id', None)
                if pid is not None:
                    tl_by_parent.setdefault(pid, []).append(t)
            if self.show_archived_tasks:
                # quando mostra arquivadas, tasks já é o conjunto arquivado
                tl_main = [t for t in tasks if not getattr(t, 'parent_task_id', None)]
                tl_by_parent = {}
                for t in tasks:
                    pid = getattr(t, 'parent_task_id', None)
                    if pid is not None:
                        tl_by_parent.setdefault(pid, []).append(t)
            timeline_items = TimelineMapper.map_tasks_to_timeline(tl_main, tl_by_parent)
            self.tab_timeline.populate(timeline_items)
        except Exception:
            import traceback
            traceback.print_exc()

        # Load Agenda
        try:
            events = [e for e in self.event_service.list_active() if e.project_id == self.project_id]
            self.tree_agenda.populate(events, self.project_service.project_repo, self.task_service.task_repo)
            
            from gui.components.timeline.timeline_mapper import TimelineMapper
            t_events = TimelineMapper.map_events_to_timeline(events)
        except Exception:
            import traceback
            traceback.print_exc()
            t_events = []

        # Load Alarms
        try:
            task_ids = [t.id for t in self.task_service.get_all_active() if t.project_id == self.project_id]
            all_alarms = self.alert_service.alert_repo.get_all(include_archived=False, include_deleted=False)
            task_alarms = [a for a in all_alarms if a.entity_type == "task" and a.entity_id in task_ids and a.status in ('pending', 'overdue')]
            proj_alarms = [a for a in all_alarms if a.entity_type == "project" and a.entity_id == self.project_id and a.status in ('pending', 'overdue')]
            alarms = task_alarms + proj_alarms
            self.tree_alarms.populate(alarms)
            
            from gui.components.timeline.timeline_mapper import TimelineMapper
            t_alarms = TimelineMapper.map_alarms_to_timeline(alarms)
            
            # Send events and alarms to Timeline
            self.tab_timeline.set_events(t_events + t_alarms)
        except Exception:
            import traceback
            traceback.print_exc()

    def _on_timeline_event_clicked(self, ev):
        """Clique simples no alarme/evento: NÃO faz nada (intencional).
        Editor abre no duplo clique ou no menu de contexto → 'Abrir'."""
        pass

    def _on_timeline_event_moved(self, ev, new_start, new_end):
        """Persiste o arraste de um alarme/evento na timeline."""
        try:
            import copy
            if ev.event_type == "alarm":
                from services.alert_service import AlertService
                svc = AlertService()
                a = svc.get_alert(ev.id)
                if not a:
                    return
                orig = copy.deepcopy(a)
                a.alert_date = new_start.strftime("%Y-%m-%d")
                a.alert_time = new_start.strftime("%H:%M") or None
                if getattr(a, "status", None) == "overdue":
                    a.status = "pending"
                svc.update_alert(a, orig)
            else:
                from services.event_service import EventService
                svc = EventService()
                e = svc.repo.get_by_id(ev.id)
                if not e:
                    return
                orig = copy.deepcopy(e)
                e.start_datetime = new_start.isoformat(sep=" ", timespec="minutes")
                if new_end is not None:
                    e.end_datetime = new_end.isoformat(sep=" ", timespec="minutes")
                svc.update(e, orig)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.load_data()
        except Exception:
            import traceback
            from PySide6.QtWidgets import QMessageBox
            traceback.print_exc()
            QMessageBox.critical(self, "Erro", "Não foi possível mover o item na linha do tempo.")
            self.load_data()

    def _on_timeline_edit_event(self, ev):
        """Duplo clique / menu de contexto em alarme ou evento → abre o editor."""
        try:
            if ev.event_type == "alarm":
                from services.alert_service import AlertService
                svc = AlertService()
                a = svc.get_alert(ev.id)
                if not a:
                    return
                task = None
                if getattr(a, "entity_type", "") == "task" and a.entity_id:
                    task = self.task_service.task_repo.get_by_id(a.entity_id)
                from gui.dialogs_qt.alarm_dialog_qt import AlarmDialogQt
                dlg = AlarmDialogQt(self, task=task, alarm=a,
                                    on_save=lambda *_: (self._emit_updated(), self.load_data()))
                dlg.exec()
            else:
                from services.event_service import EventService
                e = EventService().repo.get_by_id(ev.id)
                if not e:
                    return
                from gui.dialogs_qt.event_dialog_qt import EventDialogQt
                dlg = EventDialogQt(self, agenda_event=e)
                if dlg.exec():
                    self.load_data()
        except Exception:
            import traceback
            traceback.print_exc()

    def _emit_updated(self):
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")

    def _create_alarm_from_timeline(self, task_or_id):
        """Menu de contexto do Planejamento → 🔔 Criar Alarme na tarefa."""
        try:
            task = self._resolve_timeline_task(task_or_id)
            if task is None:
                return
            from gui.dialogs_qt.alarm_dialog_qt import AlarmDialogQt
            dialog = AlarmDialogQt(self, task=task)
            dialog.exec()
            self.load_data()
        except Exception:
            import traceback
            traceback.print_exc()

    def _create_event_from_timeline(self, task_or_id):
        """Menu de contexto do Planejamento → 📅 Criar Evento na tarefa."""
        try:
            task = self._resolve_timeline_task(task_or_id)
            if task is None:
                return
            from gui.dialogs_qt.event_dialog_qt import EventDialogQt
            dialog = EventDialogQt(self, project_id=task.project_id, task_id=task.id)
            if dialog.exec():
                self.load_data()
        except Exception:
            import traceback
            traceback.print_exc()

    def _resolve_timeline_task(self, task_or_id):
        if task_or_id is None:
            return None
        if isinstance(task_or_id, int):
            return self.task_service.task_repo.get_by_id(task_or_id)
        return task_or_id

    def _delete_timeline_event(self, ev):
        """Menu de contexto da timeline → 🗑️ Excluir alarme/evento (com confirmação)."""
        try:
            kind = "o alarme" if ev.event_type == "alarm" else "o evento"
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setWindowTitle("Confirmar")
            msg.setText(f"Deseja mesmo excluir {kind} <b>{ev.title}</b>?")
            btn_sim = msg.addButton("Sim", QMessageBox.YesRole)
            msg.addButton("Não", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() != btn_sim:
                return
            if ev.event_type == "alarm":
                from services.alert_service import AlertService
                AlertService().delete_alert(ev.id)
            else:
                from services.event_service import EventService
                EventService().delete(ev.id)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.load_data()
        except Exception:
            import traceback
            traceback.print_exc()

    def _on_timeline_task_moved(self, task_id, new_start, new_end):
        try:
            # persiste novo prazo arrastado na timeline
            import copy, datetime
            orig = self.task_service.task_repo.get_by_id(task_id)
            if not orig:
                return
            edited = copy.copy(orig)
            # Task usa datetime — converte date para datetime se necessário
            if isinstance(new_start, datetime.date) and not isinstance(new_start, datetime.datetime):
                new_start = datetime.datetime.combine(new_start, datetime.datetime.min.time())
            if isinstance(new_end, datetime.date) and not isinstance(new_end, datetime.datetime):
                new_end = datetime.datetime.combine(new_end, datetime.datetime.min.time())
            edited.start_date = new_start
            edited.due_date = new_end
            self.task_service.update_task(edited, orig)
            self.load_data()
        except Exception:
            import traceback
            traceback.print_exc()

    def edit_project(self):
        from gui.dialogs_qt.project_dialog_qt import ProjectDialogQt
        
        def save_proj(edited, is_new, original_proj=None):
            self.project_service.update_project(edited, original_proj)
            event_bus.emit("entity_updated")
            
        dlg = ProjectDialogQt(self, project=self.project, on_save=save_proj)
        dlg.exec()
        
    def new_task(self):
        from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
        from models.entities import Task
        t = Task(project_id=self.project_id)
        
        def save_task(new_t, is_new, original_t=None):
            try:
                self.task_service.create_task(
                    title=new_t.title, context=new_t.context, status=new_t.status,
                    energy_level=new_t.energy_level, project_id=new_t.project_id,
                    due_date=new_t.due_date, estimated_hours=new_t.estimated_hours,
                    is_milestone=new_t.is_milestone
                )
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Não foi possível criar a tarefa:\n{e}")
                return
            event_bus.emit("entity_updated")
            self.load_data()
        dlg = TaskDialogQt(self, task=t, on_save=save_task)
        dlg.exec()

    def edit_task(self, item):
        task = item.data(0, Qt.UserRole)
        if not task: return
        from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
        def save_task(edited, is_new, original_t=None):
            self.task_service.update_task(edited, original_t)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.load_data()
        dialog = TaskDialogQt(self, task, save_task)
        dialog.exec()

    def _edit_task_from_timeline(self, task_or_id):
        """Abre a edição da tarefa vinda do Planejamento (duplo clique ou menu de contexto)."""
        if task_or_id is None:
            return
        if isinstance(task_or_id, int):
            task = self.task_service.task_repo.get_by_id(task_or_id)
        else:
            task = task_or_id
        if task is None:
            return
        from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
        def save_task(edited, is_new, original_t=None):
            self.task_service.update_task(edited, original_t)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.load_data()
        dialog = TaskDialogQt(self, task, save_task)
        dialog.exec()

    def show_task_context_menu(self, pos):
        item = self.tbl_tasks.itemAt(pos)
        if not item: return
        task = item.data(0, Qt.UserRole)
        if not task: return
        
        menu = QMenu(self)
        
        action_open = menu.addAction("👁️ Abrir")
        action_edit = menu.addAction("✏️ Editar")
        menu.addSeparator()
        
        def create_color_icon(color_hex):
            from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor
            from PySide6.QtCore import Qt
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(color_hex))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            return QIcon(pixmap)
        
        status_menu = menu.addMenu("Mudar Status")
        for st in ["Pendente", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"]:
            color = get_status_color(st)
            action = status_menu.addAction(create_color_icon(color), st)
            action.triggered.connect(lambda checked=False, s=st, t=task: self.change_task_status(t, s))
            
        menu.addSeparator()
        
        action_alarm = menu.addAction("🔔 Criar Alarme")
        
        if getattr(task, "is_archived", False):
            action_unarchive = menu.addAction("📦 Desarquivar")
            action_unarchive.triggered.connect(lambda: self._unarchive_task(task))
        else:
            action_archive = menu.addAction("📦 Arquivar")
            action_archive.triggered.connect(lambda: self._archive_task(task))
            
        menu.addSeparator()
        action_del = menu.addAction("🗑️ Excluir")
        
        action = menu.exec(self.tbl_tasks.viewport().mapToGlobal(pos))
        if action == action_open:
            self.open_task_detail_signal.emit(task.id)
        elif action == action_edit:
            from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
            def save_task(edited, is_new, original_t=None):
                self.task_service.update_task(edited, original_t)
                from core.event_bus import event_bus
                event_bus.emit("entity_updated")
                self.load_data()
            dialog = TaskDialogQt(self, task, save_task)
            dialog.exec()
        elif action == action_alarm:
            from gui.dialogs_qt.alarm_dialog_qt import AlarmDialogQt
            dialog = AlarmDialogQt(self, task=task)
            dialog.exec()
            self.load_data()
        elif action == action_del:
            from services.link_service import LinkService
            refs = LinkService().find_references_to_entity("task", task.id)
            if refs:
                from gui.dialogs_qt.reference_warning_dialog_qt import ReferenceWarningDialog
                dlg = ReferenceWarningDialog("tarefa", task.title, refs, self, show_archive=True)
                dlg.exec()
                if dlg.action == "archive":
                    self.task_service.archive_task(task.id)
                    from core.event_bus import event_bus
                    event_bus.emit("entity_updated")
                    self.load_data()
                    return
                elif dlg.action == "delete_all":
                    LinkService().delete_all_references_to("task", task.id)
                else:
                    return
            from PySide6.QtWidgets import QMessageBox
            resp = QMessageBox.question(self, "Confirmar Exclusão", f"Deseja excluir a tarefa '{task.title}'?")
            if resp == QMessageBox.Yes:
                LinkService().delete_all_references_to("task", task.id)
                self.task_service.soft_delete_task(task.id)
                from core.event_bus import event_bus
                event_bus.emit("entity_updated")
                self.load_data()

    def change_task_status(self, task, new_status):
        self.task_service.change_status(task, new_status)
        self.load_data()

    def _archive_task(self, task):
        self.task_service.archive_task(task.id)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.load_data()

    def _unarchive_task(self, task):
        self.task_service.restore_task(task.id)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.load_data()

    def handle_row_moved(self, task_id, new_parent_id=None):
        # Persist reparenting if the item's visual parent changed
        task = self.task_service.task_repo.get_by_id(task_id)
        if task:
            current_parent = task.parent_task_id
            if (current_parent or None) != (new_parent_id or None):
                if not self.task_service.move_task(task_id, new_parent_id):
                    self.load_data()
                    return

        # target_row is not entirely accurate for trees, so we rebuild visual_tasks
        visual_tasks = []
        root = self.tbl_tasks.invisibleRootItem()
        def extract_tasks(parent):
            for i in range(parent.childCount()):
                item = parent.child(i)
                t = item.data(0, Qt.UserRole)
                if t: visual_tasks.append(t)
                extract_tasks(item)
        extract_tasks(root)
                    
        task = next((t for t in visual_tasks if t.id == task_id), None)
        if not task: return
        
        if self.active_status_filter:
            # INTERPOLAÇÃO para não reescrever posições das tarefas invisíveis
            if len(visual_tasks) < 2:
                return
            idx = next((i for i, t in enumerate(visual_tasks) if t.id == task_id), -1)
            if idx <= 0:
                new_pos = (visual_tasks[1].position - 1.0) if visual_tasks[1].position is not None else 0.0
            elif idx >= len(visual_tasks) - 1:
                new_pos = (visual_tasks[-2].position + 1.0) if visual_tasks[-2].position is not None else 0.0
            else:
                prev_pos = visual_tasks[idx - 1].position if visual_tasks[idx - 1].position is not None else 0.0
                next_pos = visual_tasks[idx + 1].position if visual_tasks[idx + 1].position is not None else 0.0
                new_pos = (prev_pos + next_pos) / 2.0
                
            task.position = new_pos
            self.task_service.update_task_position(task.id, new_pos)
        else:
            # SEM FILTRO: reescrever lista toda para forçar gap 100 e salvar ordenação visual global
            for row, t in enumerate(visual_tasks):
                new_pos = float(row * 100)
                t.position = new_pos
                self.task_service.update_task_position(t.id, new_pos)
        
        self.settings.remove("proj_tasks_sort_column")
        self.settings.remove("proj_tasks_sort_order")
        self.tbl_tasks.header().setSortIndicatorShown(False)
        
        self.load_data()
        
    def new_agenda_event(self):
        try:
            from gui.dialogs_qt.event_dialog_qt import EventDialogQt
            dialog = EventDialogQt(None, project_id=self.project_id)
            dialog.exec()
            
            self.settings.remove("proj_tasks_sort_column")
            self.settings.remove("proj_tasks_sort_order")
            self.tbl_tasks.header().setSortIndicatorShown(False)
            
            self.load_data()
        except Exception as e:
            import traceback
            import os
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN NEW_AGENDA_EVENT:\n")
                    traceback.print_exc(file=f)
            except:
                pass
        
    def handle_header_click(self, logical_index):
        header = self.tbl_tasks.header()
        
        current_col = self.settings.value("proj_tasks_sort_column", -1, type=int)
        current_order = self.settings.value("proj_tasks_sort_order", Qt.AscendingOrder.value, type=int)
        
        if current_col == logical_index:
            order = Qt.DescendingOrder if current_order == Qt.AscendingOrder.value else Qt.AscendingOrder
        else:
            order = Qt.AscendingOrder
            
        self.settings.setValue("proj_tasks_sort_column", logical_index)
        self.settings.setValue("proj_tasks_sort_order", order.value)
        
        self.tbl_tasks.setSortingEnabled(True)
        self.tbl_tasks.sortItems(logical_index, order)
        self.tbl_tasks.setSortingEnabled(False)
        
        header.setSortIndicator(logical_index, order)
        header.setSortIndicatorShown(True)

    def restore_sort_order(self):
        col = self.settings.value("proj_tasks_sort_column", -1, type=int)
        if col != -1:
            order_val = self.settings.value("proj_tasks_sort_order", Qt.AscendingOrder.value, type=int)
            order = Qt.SortOrder(order_val)
            self.tbl_tasks.setSortingEnabled(True)
            self.tbl_tasks.sortItems(col, order)
            self.tbl_tasks.setSortingEnabled(False)
            
            self.tbl_tasks.header().setSortIndicator(col, order)
            self.tbl_tasks.header().setSortIndicatorShown(True)
        else:
            self.tbl_tasks.header().setSortIndicatorShown(False)
