from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QFrame, QTabWidget, QWidget, QLineEdit,
    QGridLayout, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QInputDialog, QMessageBox, QMenu, QTreeWidget, QTreeWidgetItem, QTextBrowser
)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtWidgets import QScrollBar
from PySide6.QtWidgets import QSizePolicy
from gui.theme import get_status_color, get_energy_color, format_colored_label, format_status, get_archived_color
from PySide6.QtGui import QColor, QBrush, QAction
from services.task_service import TaskService
from services.event_service import EventService
from models.entities import Task
import json
from datetime import datetime

class TaskDetailQt(QWidget):
    go_back = Signal()

    def __init__(self, task_id, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.service = TaskService()
        self.event_service = EventService()
        self.task = self.service.task_repo.get_by_id(task_id)
        if not self.task:
            return
        self._first_show = True

        self.setup_ui()

        self._alarm_timer = QTimer(self)
        self._alarm_timer.timeout.connect(self.load_agenda)
        self._alarm_timer.start(30000)

        from core.event_bus import event_bus
        event_bus.subscribe("snapshot_updated", self.safe_load_data)
        event_bus.subscribe("entity_updated", self.safe_load_data)
        self.destroyed.connect(self._on_destroyed)

    def _on_destroyed(self):
        from core.event_bus import event_bus
        event_bus.unsubscribe("snapshot_updated", self.safe_load_data)
        event_bus.unsubscribe("entity_updated", self.safe_load_data)

    def safe_load_data(self, _=None):
        try:
            t = self.service.task_repo.get_by_id(self.task_id)
            if t:
                self.task = t
                self.lbl_title.setText(f"Tarefa #{self.task.id}: {self.task.title}")
            if self.isVisible():
                self.load_data()
        except Exception:
            pass


    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            self.load_data()
            QTimer.singleShot(50, self._adjust_all_rows)
        else:
            try:
                self.load_subtasks()
            except Exception:
                import traceback
                traceback.print_exc()

    def edit_task(self):
        from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
        from core.event_bus import event_bus
        
        def save_task(edited, is_new, original_t=None):
            self.service.update_task(edited, original_t)
            self.task = edited
            self.lbl_title.setText(f"Tarefa #{self.task.id}: {self.task.title}")
            self.load_data()
            event_bus.emit("entity_updated")
            
        dlg = TaskDialogQt(self, task=self.task, on_save=save_task)
        dlg.exec()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.btn_back = QPushButton("← Voltar")
        self.btn_back.setObjectName("secondary")
        self.btn_back.clicked.connect(self._on_back_clicked)
        header_layout.addWidget(self.btn_back)
        
        self.lbl_title = QLabel(f"Tarefa #{self.task.id}: {self.task.title}")
        self.lbl_title.setObjectName("header")
        self.lbl_title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.lbl_title, stretch=1)
        
        self.btn_edit = QPushButton("✏️ Editar Tarefa")
        self.btn_edit.setObjectName("secondary")
        self.btn_edit.clicked.connect(self.edit_task)
        header_layout.addWidget(self.btn_edit)

        header_layout.addSpacing(20)
        from gui.components.references_panel_qt import ReferencesPanelQt
        self.refs_panel = ReferencesPanelQt(entity_type="task", entity_id=self.task.id, parent=self)
        header_layout.addWidget(self.refs_panel)

        main_layout.addLayout(header_layout)
        
        # Tabs
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
        
        self.tab_geral = QWidget()
        self.setup_geral_tab()
        self.tabs.addTab(self.tab_geral, "Geral")
        
        from gui.views.ideas_qt import IdeasQt
        self.tab_ideas = IdeasQt(project_id=self.task.project_id, task_id=self.task_id)
        self.tabs.addTab(self.tab_ideas, "Ideias")
        
        # Alarmes e Eventos no nível das abas principais (aba Agenda removida)
        self.setup_agenda_tabs()

        main_layout.addWidget(self.tabs)
        self._init_tab_navigation()

        
    def setup_geral_tab(self):
        layout = QVBoxLayout(self.tab_geral)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Status:"), 0, 0)
        ts = format_status(self.task.status, getattr(self.task, 'is_archived', False))
        sc = get_archived_color() if getattr(self.task, 'is_archived', False) else get_status_color(self.task.status)
        lbl_status = QLabel(ts)
        lbl_status.setStyleSheet(f"color: {sc}; font-weight: bold;")
        grid.addWidget(lbl_status, 0, 1)
        
        grid.addWidget(QLabel("Prioridade:"), 1, 0)
        lbl_prio = QLabel(self.task.energy_level)
        lbl_prio.setStyleSheet(f"color: {get_energy_color(self.task.energy_level)}; font-weight: bold;")
        grid.addWidget(lbl_prio, 1, 1)
        
        grid.addWidget(QLabel("Projeto ID:"), 2, 0)
        grid.addWidget(QLabel(str(self.task.project_id) if self.task.project_id else "Nenhum"), 2, 1)
        
        grid.addWidget(QLabel("Prazo Final:"), 3, 0)
        due_str = "Sem data"
        if self.task.due_date:
            try:
                import datetime
                dt = datetime.datetime.fromisoformat(str(self.task.due_date))
                due_str = dt.strftime("%d/%m/%Y")
            except:
                due_str = str(self.task.due_date).split()[0]
        grid.addWidget(QLabel(due_str), 3, 1)
        
        layout.addLayout(grid)
        
        layout.addWidget(QLabel("Contexto:"))
        self.txt_desc = QTextEdit()
        self.txt_desc.setReadOnly(True)
        self.txt_desc.setStyleSheet("background-color: #1c1c2e; border: 1px solid #2a2a3f; border-radius: 5px;")
        self.txt_desc.setPlainText(self.task.context or "Sem contexto.")
        self.txt_desc.setMaximumHeight(80)
        layout.addWidget(self.txt_desc)
        
        header_sub = QHBoxLayout()
        lbl_sub = QLabel("Subtarefas:")
        lbl_sub.setStyleSheet("font-weight: bold; margin-top: 10px;")
        header_sub.addWidget(lbl_sub)
        header_sub.addStretch()
        btn_add_sub = QPushButton("➕ Nova Subtarefa")
        btn_add_sub.setObjectName("secondary")
        btn_add_sub.clicked.connect(self.new_subtask)
        header_sub.addWidget(btn_add_sub)
        layout.addLayout(header_sub)
        
        from gui.components.drag_drop_tree_qt import DragDropTreeWidget
        self.tbl_subtasks = DragDropTreeWidget()
        self.tbl_subtasks.setColumnCount(5)
        self.tbl_subtasks.setHeaderLabels(["ID", "Título", "Status", "Prazo", "Progresso"])
        self.tbl_subtasks.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_subtasks.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_subtasks.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_subtasks.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_subtasks.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_subtasks.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_subtasks.setAlternatingRowColors(True)
        self.tbl_subtasks.itemDoubleClicked.connect(self.open_subtask)
        self.tbl_subtasks.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_subtasks.customContextMenuRequested.connect(self.show_subtasks_context_menu)
        self.tbl_subtasks.item_moved.connect(self._subtask_moved)
        self.tbl_subtasks.set_drop_root_parent(self.task.id)

        from gui.components.badge_delegate import BadgeDelegate
        from gui.components.progress_bar_delegate import ProgressBarDelegate
        self.tbl_subtasks.setItemDelegateForColumn(2, BadgeDelegate("status", parent=self.tbl_subtasks))
        self.tbl_subtasks.setItemDelegateForColumn(4, ProgressBarDelegate(parent=self.tbl_subtasks))
        layout.addWidget(self.tbl_subtasks)
        
        # Header com título e botão na mesma linha
        header_logs = QHBoxLayout()
        lbl_logs = QLabel("Atividades / Logs:")
        lbl_logs.setStyleSheet("font-weight: bold; margin-top: 10px;")
        header_logs.addWidget(lbl_logs)
        header_logs.addStretch()
        btn_add = QPushButton("📝 + Nova Atividade")
        btn_add.setObjectName("secondary")
        btn_add.clicked.connect(self.add_activity)
        header_logs.addWidget(btn_add)
        layout.addLayout(header_logs)
        
        self.tbl_logs = QTableWidget()
        self.tbl_logs.setColumnCount(3)
        self.tbl_logs.setHorizontalHeaderLabels(["Data", "Ação", "Detalhes"])
        self.tbl_logs.setWordWrap(True)
        self.tbl_logs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_logs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_logs.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tbl_logs.setAlternatingRowColors(True)
        self.tbl_logs.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_logs.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_logs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl_logs.customContextMenuRequested.connect(self.show_logs_context_menu)
        self.tbl_logs.horizontalHeader().sectionResized.connect(lambda: QTimer.singleShot(0, self._adjust_all_rows))
        layout.addWidget(self.tbl_logs)
        
    def get_activity_text(self, title, default_text=""):
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout
        from gui.widgets.wiki_text_edit import WikiTextEdit
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(600, 300)

        layout = QVBoxLayout(dialog)
        text_edit = WikiTextEdit()
        text_edit.setPlainText(default_text)        
        text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        layout.addWidget(text_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec() == QDialog.Accepted:
            return text_edit.toPlainText(), True
        return "", False
            
    def add_activity(self):
        text, ok = self.get_activity_text("Nova Atividade")
        if ok and text.strip():
            from database.repositories.activity_log_repository import ActivityLogRepository, ActivityLog
            repo = ActivityLogRepository()
            log = ActivityLog(entity_type="task", entity_id=self.task.id, action="MANUAL", changed_fields_json=text.strip())
            repo.create(log)
            self.load_data()
            
    def show_logs_context_menu(self, pos):
        index = self.tbl_logs.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        log_id = self.tbl_logs.item(row, 0).data(Qt.UserRole)
        action_type = self.tbl_logs.item(row, 1).text()
        
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2a2a3f; color: white; } QMenu::item:selected { background-color: #4a6fe3; }")
        
        if action_type == "COMENTÁRIO":
            action_edit = QAction("\u270f\ufe0f Editar", self)
            action_edit.triggered.connect(lambda: self.edit_activity(log_id, row))
            menu.addAction(action_edit)
            
        action_delete = QAction("\U0001f5d1\ufe0f Excluir", self)
        action_delete.triggered.connect(lambda: self.delete_activity(log_id))
        menu.addAction(action_delete)
        
        menu.exec_(self.tbl_logs.viewport().mapToGlobal(pos))
        
    def edit_activity(self, log_id, row):
        tb = self.tbl_logs.cellWidget(row, 2)
        full_text = tb.property("raw_text") if tb else ""
        text, ok = self.get_activity_text("Editar Atividade", full_text)
        if ok and text.strip():
            from database.repositories.activity_log_repository import ActivityLogRepository
            repo = ActivityLogRepository()
            repo.update_changed_fields(log_id, text.strip())
            self.load_data()
            
    def delete_activity(self, log_id):
        reply = QMessageBox.question(self, "Confirmar", "Tem certeza que deseja excluir esta atividade?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            from database.repositories.activity_log_repository import ActivityLogRepository
            repo = ActivityLogRepository()
            repo.delete(log_id)
            self.load_data()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel and isinstance(obj, QScrollBar):
            return True
        return super().eventFilter(obj, event)

    def _adjust_all_rows(self):
        for row in range(self.tbl_logs.rowCount()):
            tb = self.tbl_logs.cellWidget(row, 2)
            if tb:
                self._adjust_log_row(row, tb)

    def _adjust_log_row(self, row, tb):
        vw = self.tbl_logs.viewport().width()
        c0 = self.tbl_logs.columnWidth(0)
        c1 = self.tbl_logs.columnWidth(1)
        c2 = vw - c0 - c1 - 8
        if c2 < 100:
            c2 = 400
        tb.document().setDocumentMargin(3)
        tb.document().setTextWidth(c2 - 6)
        h = tb.document().size().height()
        self.tbl_logs.setRowHeight(row, max(int(h) + 16, 36))

    def _on_activity_link_clicked(self, url):
        scheme = url.scheme()
        if scheme == "app":
            t_type = url.host()
            t_id_str = url.path().strip("/")
            if t_id_str.isdigit():
                from core.event_bus import event_bus
                event_bus.emit("navigate_to", {"type": t_type, "id": int(t_id_str)})
        elif scheme == "file":
            f_uuid = url.path().strip("/")
            if not f_uuid:
                return
            from database.connection import get_db_cursor
            try:
                with get_db_cursor() as cursor:
                    cursor.execute("SELECT * FROM attachments WHERE deleted_at IS NULL")
                    rows = cursor.fetchall()
                from models.entities import Attachment
                for row in rows:
                    att = Attachment(**dict(row))
                    if att.uuid == f_uuid:
                        import subprocess, os
                        if os.path.exists(att.file_path):
                            subprocess.Popen(["explorer", att.file_path] if os.name == "nt" else ["xdg-open", att.file_path])
                        break
            except Exception:
                pass


    def load_subtasks(self):
        from gui.components.drag_drop_tree_qt import SortableTreeWidgetItem
        svc = self.service
        all_tasks = svc.task_repo.get_all(include_archived=True, include_deleted=False)
        children = {}
        for t in all_tasks:
            pid = getattr(t, 'parent_task_id', None)
            if pid is not None:
                children.setdefault(pid, []).append(t)

        self.tbl_subtasks.setSortingEnabled(False)
        self.tbl_subtasks.clear()

        def sort_key(t):
            pos = getattr(t, 'position', None)
            return (pos if pos is not None else float('inf'), getattr(t, 'id', 0) or 0)

        for pid in list(children.keys()):
            children[pid].sort(key=sort_key)

        def compute_progress(t):
            subs = children.get(t.id, [])
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

            if depth > 0:
                from PySide6.QtGui import QColor as _QC
                if depth >= 2:
                    item.setForeground(1, QBrush(_QC("#b06ab3")))
                    bg = _QC(176, 106, 179, 22)
                else:
                    item.setForeground(1, QBrush(_QC("#e67e22")))
                    bg = _QC(230, 126, 34, 18)
                for _c in range(self.tbl_subtasks.columnCount()):
                    item.setBackground(_c, QBrush(bg))

            from gui.theme import format_status
            item.setText(2, format_status(t.status, getattr(t, 'is_archived', False)))
            item.setTextAlignment(2, Qt.AlignCenter)

            due_str = "-"
            if t.due_date:
                try:
                    import datetime
                    dt = datetime.datetime.fromisoformat(str(t.due_date))
                    due_str = dt.strftime("%d/%m/%Y")
                except:
                    due_str = str(t.due_date).split()[0]
            item.setText(3, due_str)
            item.setTextAlignment(3, Qt.AlignCenter)

            progress_str = compute_progress(t)
            if progress_str:
                item.setText(4, progress_str)
                try:
                    done = int(progress_str.split("/")[0])
                    total = int(progress_str.split("/")[1])
                    item.sort_values[4] = done / total if total else 0.0
                except (ValueError, IndexError):
                    pass
            else:
                item.setText(4, "")
            item.setTextAlignment(4, Qt.AlignCenter)

            for sub_t in children.get(t.id, []):
                create_tree_item(sub_t, item, depth + 1)
            return item

        for st in children.get(self.task.id, []):
            create_tree_item(st, self.tbl_subtasks, 0)

        from gui.components.drag_drop_tree_qt import fit_branch_arrows
        fit_branch_arrows(self.tbl_subtasks)
        self.tbl_subtasks.expandAll()

    def _subtask_moved(self, task_id, new_parent_id=None):
        if not self.service.move_task(task_id, new_parent_id):
            self.load_subtasks()
            return
        # Reescrever posições na ordem visual atual (para persistir reordenações
        # dentro do mesmo pai e a posição do item movido)
        self._persist_subtree_order()
        self.load_subtasks()
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")

    def _persist_subtree_order(self):
        """Persiste a posição de todas as subtarefas conforme a ordem visual atual
        da árvore, atribuindo gaps de 100 a cada irmão (mesma parent_task_id)."""
        svc = self.service
        children_by_parent = {}
        root = self.tbl_subtasks.invisibleRootItem()
        stack = []

        def collect(parent, pid):
            for i in range(parent.childCount()):
                item = parent.child(i)
                t = item.data(0, Qt.UserRole)
                if t:
                    children_by_parent.setdefault(pid, []).append(t)
                collect(item, t.id if t else pid)
        collect(root, None)

        for pid, tasks in children_by_parent.items():
            for row, t in enumerate(tasks):
                new_pos = float((row + 1) * 100)
                if (t.position or 0.0) == new_pos:
                    continue
                t.position = new_pos
                svc.update_task_position(t.id, new_pos)
            
    def new_subtask(self):
        from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
        from models.entities import Task
        
        new_t = Task(project_id=self.task.project_id, parent_task_id=self.task.id)
        
        def save_subtask(saved_t, is_new, original_t=None):
            try:
                from services.task_service import TaskService
                svc = TaskService()
                svc.create_task(
                    title=saved_t.title,
                    context=saved_t.context,
                    status=saved_t.status,
                    energy_level=saved_t.energy_level,
                    project_id=saved_t.project_id,
                    parent_task_id=saved_t.parent_task_id,
                    start_date=saved_t.start_date,
                    due_date=saved_t.due_date,
                    estimated_hours=saved_t.estimated_hours,
                    is_milestone=saved_t.is_milestone
                )
                self.load_subtasks()
                from core.event_bus import event_bus
                event_bus.emit("entity_updated")
            except Exception as e:
                import traceback
                print("Error saving subtask:", e)
                traceback.print_exc()

        dialog = TaskDialogQt(self, task=new_t, on_save=save_subtask)
        dialog.exec()
        
    def open_subtask(self, item, column=None):
        task = item.data(0, Qt.UserRole)
        if not task:
            return
        from core.event_bus import event_bus
        event_bus.emit("navigate_to", {"type": "task", "id": task.id})

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

    def _subtask_at(self, pos):
        item = self.tbl_subtasks.itemAt(pos)
        if item is None:
            return None, None
        task = item.data(0, Qt.UserRole)
        return task, None

    def show_subtasks_context_menu(self, pos):
        task, row = self._subtask_at(pos)
        if task is None:
            return

        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2a2a3f; color: white; } QMenu::item:selected { background-color: #4a6fe3; }")

        action_open = menu.addAction("👁️ Abrir")
        action_edit = menu.addAction("✏️ Editar")

        def create_color_icon(color_hex):
            from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor
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
        from gui.theme import get_status_color
        for st in ["Pendente", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"]:
            action = status_menu.addAction(create_color_icon(get_status_color(st)), st)
            action.triggered.connect(lambda checked=False, s=st, t=task: self._change_subtask_status(t, s))

        menu.addSeparator()
        action_alarm = menu.addAction("🔔 Criar Alarme")
        action_archive = None
        action_unarchive = None

        if getattr(task, "is_archived", False):
            action_unarchive = menu.addAction("📦 Desarquivar")
        else:
            action_archive = menu.addAction("📦 Arquivar")

        menu.addSeparator()
        action_del = menu.addAction("🗑️ Excluir")

        action = menu.exec(self.tbl_subtasks.viewport().mapToGlobal(pos))
        if action == action_open:
            from core.event_bus import event_bus
            event_bus.emit("navigate_to", {"type": "task", "id": task.id})
        elif action == action_edit:
            self._edit_subtask(task)
        elif action == action_alarm:
            from gui.dialogs_qt.alarm_dialog_qt import AlarmDialogQt
            dlg = AlarmDialogQt(self, task=task)
            dlg.exec()
            self.load_subtasks()
        elif action == action_archive:
            self.service.archive_task(task.id)
            self.load_subtasks()
        elif action == action_unarchive:
            self.service.restore_task(task.id)
            self.load_subtasks()
        elif action == action_del:
            self._delete_subtask(task)

    def _change_subtask_status(self, task, new_status):
        self.service.change_status(task, new_status)
        self.load_subtasks()
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")

    def _edit_subtask(self, task):
        from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
        def save_sub(edited, is_new, original_t=None):
            self.service.update_task(edited, original_t)
            self.load_subtasks()
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
        dlg = TaskDialogQt(self, task=task, on_save=save_sub)
        dlg.exec()

    def _delete_subtask(self, task):
        from services.link_service import LinkService
        refs = LinkService().find_references_to_entity("task", task.id)
        if refs:
            from gui.dialogs_qt.reference_warning_dialog_qt import ReferenceWarningDialog
            dlg = ReferenceWarningDialog("tarefa", task.title, refs, self, show_archive=True)
            dlg.exec()
            if dlg.action == "archive":
                self.service.archive_task(task.id)
                self.load_subtasks()
                return
            elif dlg.action == "delete_all":
                LinkService().delete_all_references_to("task", task.id)
            else:
                return
        from PySide6.QtWidgets import QMessageBox
        resp = QMessageBox.question(self, "Confirmar Exclusão", f"Deseja excluir a subtarefa '{task.title}'?")
        if resp == QMessageBox.Yes:
            LinkService().delete_all_references_to("task", task.id)
            self.service.soft_delete_task(task.id)
            self.load_subtasks()
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")

    def load_data(self):
        self.load_subtasks()
        # Load Logs
        from database.repositories.activity_log_repository import ActivityLogRepository
        repo = ActivityLogRepository()
        logs = repo.get_by_entity("task", self.task.id)
        
        action_translation = {
            "CREATED": "CRIADO",
            "UPDATED": "ATUALIZADO",
            "STATUS_CHANGED": "MUDANÇA DE STATUS",
            "MANUAL": "COMENTÁRIO",
            "ARCHIVED": "ARQUIVADO",
            "RESTORED": "RESTAURADO",
            "DEADLINE_CREATED": "PRAZO ESTIMADO",
            "DEADLINE_UPDATED": "PRAZO ESTIMADO",
            "DEADLINE_REMOVED": "PRAZO ESTIMADO"
        }
        
        color_mapping = {
            "CRIADO": "#4caf50",
            "ATUALIZADO": "#2196f3",
            "MUDANÇA DE STATUS": "#ff9800",
            "COMENTÁRIO": "#e91e63",
            "PRAZO ESTIMADO": "#f44336"
        }
        
        self.tbl_logs.setRowCount(0)
        for i, log in enumerate(logs):
            self.tbl_logs.insertRow(i)
            
            # Format Date
            try:
                dt = datetime.fromisoformat(str(log.created_at).split('.')[0])
                date_str = dt.strftime("%d/%m/%Y %H:%M")
            except:
                date_str = str(log.created_at)
                
            item_date = QTableWidgetItem(date_str)
            item_date.setData(Qt.UserRole, log.id)
            self.tbl_logs.setItem(i, 0, item_date)
            
            # Retrocompatibility for old MANUAL_NOTE
            if log.action.upper() == "MANUAL_NOTE":
                log.action = "MANUAL"
                try:
                    parsed = json.loads(log.changed_fields_json)
                    if "note" in parsed:
                        log.changed_fields_json = parsed["note"]
                except:
                    pass
            
            action_pt = action_translation.get(log.action, log.action)
            item_action = QTableWidgetItem(action_pt)
            item_action.setTextAlignment(Qt.AlignCenter)
            item_action.setForeground(QBrush(QColor(color_mapping.get(action_pt, "#ffffff"))))
            self.tbl_logs.setItem(i, 1, item_action)
            
            details = log.changed_fields_json or ""
            if log.action == "ARCHIVED":
                details = "Tarefa arquivada"
            elif log.action == "RESTORED":
                details = "Tarefa restaurada"
            elif log.action not in ("MANUAL", "COMENTÁRIO") and details:
                try:
                    parsed = json.loads(details)
                    field_translations = {
                        "title": "título",
                        "due_date": "prazo",
                        "energy_level": "prioridade",
                        "status": "status",
                        "alert_date": "data do alerta",
                        "alert_message": "mensagem do alerta",
                        "context": "contexto",
                        "project_id": "projeto"
                    }
                    
                    def fmt_val(val):
                        if val is None or val == "None" or str(val).strip() == "":
                            return "vazio"
                        return str(val)

                    if log.action == "CREATED":
                        parts = []
                        title_val = self.task.title
                        for k, v in parsed.items():
                            if k == "title":
                                title_val = fmt_val(v.get('to'))
                                continue
                            parts.append(f"{field_translations.get(k, k)} {fmt_val(v.get('to'))}")
                        if parts:
                            details = f"Criação da tarefa '{title_val}' com " + ", ".join(parts)
                        else:
                            details = f"Criação da tarefa '{title_val}'"
                            
                    elif log.action == "UPDATED":
                        parts = []
                        for k, v in parsed.items():
                            if k == "parent_task_id":
                                to_val = v.get('to') if isinstance(v, dict) else v
                                if not to_val:
                                    parts.append("virou tarefa raiz")
                                else:
                                    try:
                                        from database.repositories.task_repository import TaskRepository
                                        parent = TaskRepository().get_by_id(int(to_val))
                                        parent_name = f"'{parent.title}'" if parent else f"id {to_val}"
                                    except Exception:
                                        parent_name = f"id {to_val}"
                                    parts.append(f"virou filho de {parent_name}")
                                continue
                            k_pt = field_translations.get(k, k)
                            from_v = fmt_val(v.get('from'))
                            to_v = fmt_val(v.get('to'))
                            parts.append(f"{k_pt} de '{from_v}' para '{to_v}'")
                        details = f"Alteração da tarefa '{self.task.title}' - " + ", ".join(parts)
                        
                    elif log.action == "STATUS_CHANGED":
                        if "status" in parsed:
                            from_v = fmt_val(parsed["status"].get('from'))
                            to_v = fmt_val(parsed["status"].get('to'))
                            details = f"Mudança de status de '{from_v}' para '{to_v}'"
                        else:
                            details = "Mudança de status"

                    elif log.action in ("DEADLINE_CREATED", "DEADLINE_UPDATED"):
                        date_val = fmt_val(parsed.get("estimated_deadline", {}).get('to')) if "estimated_deadline" in parsed else ""
                        desc_val = (parsed.get("estimated_deadline_desc", {}) or {}).get('to') or ""
                        verb = "Criação" if log.action == "DEADLINE_CREATED" else "Alteração"
                        details = f"{verb} do Prazo Estimado para {date_val}" if date_val else f"{verb} do Prazo Estimado"
                        if desc_val:
                            details += f" — descrição: {desc_val}"

                    elif log.action == "DEADLINE_REMOVED":
                        date_val = fmt_val(parsed.get("estimated_deadline", {}).get('to')) if "estimated_deadline" in parsed else ""
                        desc_val = (parsed.get("estimated_deadline_desc", {}) or {}).get('to') or ""
                        details = "Remoção do Prazo Estimado"
                        if date_val:
                            details += f" ({date_val})"
                        if desc_val:
                            details += f" — descrição: {desc_val}"
                            
                    else:
                        details = ", ".join(f"{field_translations.get(k, k)} de '{fmt_val(v.get('from'))}' para '{fmt_val(v.get('to'))}'" for k,v in parsed.items())
                except:
                    pass
                    
            from gui.widgets.wiki_text_edit import render_links_as_html
            html = render_links_as_html(details) or details
            tb = QTextBrowser()
            tb.setProperty("raw_text", details)
            tb.setOpenLinks(False)
            tb.setContextMenuPolicy(Qt.NoContextMenu)
            tb.anchorClicked.connect(lambda url: self._on_activity_link_clicked(url))
            style = "margin:0;padding:0;color:#e0e0e0;font-size:12px;"
            tb.setHtml(f"<div style='{style}'>{html}</div>" if html else "")
            tb.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            tb.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            tb.setStyleSheet("background: transparent; border: none; padding: 0px; margin: 0px;")
            tb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tb.verticalScrollBar().installEventFilter(self)
            self.tbl_logs.setCellWidget(i, 2, tb)

        self.load_agenda()
        QTimer.singleShot(0, self._adjust_all_rows)

    def setup_agenda_tabs(self):
        # Aba Alarmes
        tab_alarmes = QWidget()
        layout_alarmes = QVBoxLayout(tab_alarmes)
        layout_alarmes.setSpacing(8)
        layout_alarmes.setContentsMargins(4, 4, 4, 4)

        alarm_header = QHBoxLayout()
        alarm_header.addStretch()
        self.btn_new_alarm = QPushButton("🔔 + Novo Alarme")
        self.btn_new_alarm.setObjectName("secondary")
        self.btn_new_alarm.clicked.connect(self.new_alarm)
        alarm_header.addWidget(self.btn_new_alarm)
        layout_alarmes.addLayout(alarm_header)

        from gui.components.alarm_cards_qt import AlarmCardsWidget
        self.tree_alarms = AlarmCardsWidget(grouping="date", filter_project_id=self.task.project_id, filter_task_id=None, highlight_task_id=self.task.id, main_window=self.window(), parent=self)
        layout_alarmes.addWidget(self.tree_alarms)
        self.tabs.addTab(tab_alarmes, "Alarmes")
        
        # Aba Eventos
        tab_eventos = QWidget()
        layout_eventos = QVBoxLayout(tab_eventos)
        layout_eventos.setSpacing(8)
        layout_eventos.setContentsMargins(4, 4, 4, 4)
        
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        self.btn_new_event = QPushButton("🔔 + Novo Evento (Alerta)")
        self.btn_new_event.setObjectName("secondary")
        self.btn_new_event.clicked.connect(self.new_agenda_event)
        header_layout.addWidget(self.btn_new_event)
        layout_eventos.addLayout(header_layout)
        
        from gui.components.agenda_tree_qt import AgendaTreeWidget
        self.tree_agenda = AgendaTreeWidget(grouping="date", filter_project_id=self.task.project_id, filter_task_id=None, highlight_task_id=self.task.id, main_window=self.window(), parent=self)
        layout_eventos.addWidget(self.tree_agenda)
        self.tabs.addTab(tab_eventos, "Eventos")
        
    def new_agenda_event(self):
        try:
            from gui.dialogs_qt.event_dialog_qt import EventDialogQt
            dialog = EventDialogQt(None, project_id=self.task.project_id, task_id=self.task.id)
            dialog.exec()
            self.load_data()
        except Exception as e:
            import traceback
            import os
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN NEW_AGENDA_EVENT (task_detail):\n")
                    traceback.print_exc(file=f)
            except:
                pass

    def new_alarm(self):
        try:
            from gui.dialogs_qt.alarm_dialog_qt import AlarmDialogQt
            dialog = AlarmDialogQt(self, task=self.task)
            dialog.exec()
            self.load_data()
        except Exception:
            import traceback
            import os
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN NEW_ALARM (task_detail):\n")
                    traceback.print_exc(file=f)
            except:
                pass
        
    def load_agenda(self):
        if not self.isVisible():
            return
        from services.alert_service import AlertService
        AlertService().mark_overdue_alerts()
        # Load Agenda for the project
        try:
            events = [e for e in self.event_service.list_active() if e.project_id == self.task.project_id]
            from services.project_service import ProjectService
            from services.task_service import TaskService
            self.tree_agenda.populate(events, ProjectService().project_repo, TaskService().task_repo)
        except Exception:
            import traceback
            traceback.print_exc()

        # Load Alarms — somente desta tarefa + descendentes (sem alarmes do pai)
        try:
            from services.alert_service import AlertService
            alert_service = AlertService()
            subtree_ids = {self.task.id} | set(self.service.get_descendant_ids(self.task.id))
            all_alarms = alert_service.alert_repo.get_all(include_archived=False, include_deleted=False)
            task_alarms = [
                a for a in all_alarms
                if a.entity_type == "task" and a.entity_id in subtree_ids and a.status in ('pending', 'overdue')
            ]
            self.tree_alarms.populate(task_alarms)
        except Exception:
            import traceback
            traceback.print_exc()
