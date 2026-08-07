from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QHeaderView, QAbstractItemView, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSettings
from gui.components.drag_drop_tree_qt import DragDropTreeWidget, SortableTreeWidgetItem
from services.task_service import TaskService
from services.project_service import ProjectService

from gui.theme import get_status_color, get_energy_color, format_status


class TasksQt(QWidget):
    open_task_detail_signal = Signal(int)

    def __init__(self):
        super().__init__()
        self.service = TaskService()
        self.project_service = ProjectService()
        self.projects_cache = {p.id: p.name for p in self.project_service.get_all_active()}
        self.show_archived = False
        self.settings = QSettings("Solinftec", "CentralGestao")
        
        self.setup_ui()
        self.load_data()
        self.restore_sort_order()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header Area
        header_layout = QHBoxLayout()
        self.header = QLabel("Tarefas")
        self.header.setObjectName("header")
        self.header.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.header, stretch=1)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filtrar tarefas (ID, Título, Período)...")
        self.search_bar.setStyleSheet("padding: 5px; border-radius: 5px; background-color: #13131f; color: white; border: 1px solid #2a2a3f; max-width: 280px;")
        self.search_bar.textChanged.connect(self.load_data)
        header_layout.addWidget(self.search_bar)

        self.btn_archived = QPushButton("📦 Arquivados: OFF")
        self.btn_archived.setObjectName("secondary")
        self.btn_archived.setCheckable(True)
        self.btn_archived.clicked.connect(self.toggle_archived)
        header_layout.addWidget(self.btn_archived)
        
        self.btn_new = QPushButton("📋 + Nova Tarefa")
        self.btn_new.setObjectName("secondary")
        self.btn_new.clicked.connect(self.open_new_dialog)
        header_layout.addWidget(self.btn_new)
        
        main_layout.addLayout(header_layout)
        
        from core.event_bus import event_bus
        event_bus.subscribe("snapshot_updated", self.safe_load_data)
        event_bus.subscribe("entity_updated", self.safe_load_data)
        self.destroyed.connect(self._cleanup_snapshot)

        # Tree Area
        self.table = DragDropTreeWidget()
        self.table.setColumnCount(5)
        self.table.setHeaderLabels(["ID", "Título", "Status", "Projeto", "Período"])
        self.table.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.itemDoubleClicked.connect(self.open_task_detail)
        
        self.table.item_moved.connect(self.handle_row_moved)
        self.table.header().sectionClicked.connect(self.handle_header_click)
        
        # Context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.table.setAlternatingRowColors(True)
        from gui.components.badge_delegate import BadgeDelegate
        self.table.setItemDelegateForColumn(2, BadgeDelegate("status", parent=self.table))
        main_layout.addWidget(self.table, stretch=1)

    def _cleanup_snapshot(self):
        from core.event_bus import event_bus
        event_bus.unsubscribe("snapshot_updated", self.safe_load_data)

    def save_page(self): pass

    def safe_load_data(self, _=None):
        try:
            self.load_data()
        except RuntimeError:
            pass
        
    def open_new_dialog(self):
        from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
        dialog = TaskDialogQt(self, on_save=self.handle_save)
        dialog.exec()
        
    def handle_save(self, task, is_new, original_task=None):
        if is_new:
            self.service.create_task(
                title=task.title, context=task.context, status=task.status,
                energy_level=task.energy_level, project_id=task.project_id,
                start_date=task.start_date, due_date=task.due_date,
                estimated_hours=task.estimated_hours, is_milestone=task.is_milestone
            )
        else:
            self.service.update_task(task, original_task)

        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.load_data()
        
    def handle_row_moved(self, task_id, new_parent_id=None):
        # Persist reparenting if the item's visual parent changed
        task = self.service.task_repo.get_by_id(task_id)
        if task:
            current_parent = task.parent_task_id
            if (current_parent or None) != (new_parent_id or None):
                if not self.service.move_task(task_id, new_parent_id):
                    self.load_data()
                    return

        visual_tasks = []
        root = self.table.invisibleRootItem()
        def extract_tasks(parent):
            for i in range(parent.childCount()):
                it = parent.child(i)
                t = it.data(0, Qt.UserRole)
                if t:
                    visual_tasks.append(t)
                extract_tasks(it)
        extract_tasks(root)
                    
        task = next((t for t in visual_tasks if t.id == task_id), None)
        if not task: return
        
        # Agora salvamos essa nova ordem como a oficial manual
        for row, t in enumerate(visual_tasks):
            new_pos = float(row * 100)
            t.position = new_pos
            self.service.update_task_position(t.id, new_pos)
        
        # Limpar organização de coluna pois agora é manual
        self.settings.remove("tasks_sort_column")
        self.settings.remove("tasks_sort_order")
        self.table.header().setSortIndicatorShown(False)
        
        self.load_data()
        
    def handle_header_click(self, logical_index):
        header = self.table.header()
        
        current_col = self.settings.value("tasks_sort_column", -1, type=int)
        current_order = self.settings.value("tasks_sort_order", Qt.AscendingOrder.value, type=int)
        
        if current_col == logical_index:
            order = Qt.DescendingOrder if current_order == Qt.AscendingOrder.value else Qt.AscendingOrder
        else:
            order = Qt.AscendingOrder
            
        self.settings.setValue("tasks_sort_column", logical_index)
        self.settings.setValue("tasks_sort_order", order.value)
        
        # Ordenar e desligar para permitir drag and drop
        self.table.setSortingEnabled(True)
        self.table.sortItems(logical_index, order)
        self.table.setSortingEnabled(False)
        
        header.setSortIndicator(logical_index, order)
        header.setSortIndicatorShown(True)

    def restore_sort_order(self):
        col = self.settings.value("tasks_sort_column", -1, type=int)
        if col != -1:
            order_val = self.settings.value("tasks_sort_order", Qt.AscendingOrder.value, type=int)
            order = Qt.SortOrder(order_val)
            self.table.setSortingEnabled(True)
            self.table.sortItems(col, order)
            self.table.setSortingEnabled(False)
            
            self.table.header().setSortIndicator(col, order)
            self.table.header().setSortIndicatorShown(True)
        else:
            self.table.header().setSortIndicatorShown(False)

    def toggle_archived(self):
        self.show_archived = self.btn_archived.isChecked()
        self.btn_archived.setText(f"📦 Arquivados: {'ON' if self.show_archived else 'OFF'}")
        self.load_data()
        
    def open_task_detail(self, item, column=None):
        task = item.data(0, Qt.UserRole)
        if not task: return
        self.open_task_detail_signal.emit(task.id)
        
    def edit_task(self, item):
        task = item.data(0, Qt.UserRole)
        if not task: return
        from gui.dialogs_qt.task_dialog_qt import TaskDialogQt
        dialog = TaskDialogQt(self, task, self.handle_save)
        dialog.exec()
        
    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        task = item.data(0, Qt.UserRole)
        if not task: return
        
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        act_open = menu.addAction("🗂️ Abrir")
        act_open.triggered.connect(lambda: self.open_task_detail(item))
        
        if task.is_archived:
            act_restore = menu.addAction("♻️ Desarquivar")
            act_restore.triggered.connect(lambda: self._restore_task(task))
        else:
            act_edit = menu.addAction("✏️ Editar")
            act_edit.triggered.connect(lambda: self.edit_task(item))
            
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
            from gui.theme import get_status_color
            for st in ["Pendente", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"]:
                action = status_menu.addAction(st)
                action.setIcon(create_color_icon(get_status_color(st)))
                action.triggered.connect(lambda checked=False, s=st, t=task: self._change_task_status(t, s))

            menu.addSeparator()
            
            act_archive = menu.addAction("📥 Arquivar")
            act_archive.triggered.connect(lambda: self._archive_task(task))
            
        menu.addSeparator()
        
        act_del = menu.addAction("🗑️ Excluir")
        act_del.triggered.connect(lambda: self._delete_task(task))
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))
        
    def _change_task_status(self, task, status):
        task.status = status
        self.service.update_task(task, task)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.load_data()
        
    def _archive_task(self, task):
        self.service.archive_task(task.id)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.load_data()
        
    def _restore_task(self, task):
        self.service.restore_task(task.id)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.load_data()
        
    def _delete_task(self, task):
        from services.link_service import LinkService
        refs = LinkService().find_references_to_entity("task", task.id)
        if refs:
            from gui.dialogs_qt.reference_warning_dialog_qt import ReferenceWarningDialog
            dlg = ReferenceWarningDialog("tarefa", task.title, refs, self, show_archive=True)
            dlg.exec()
            if dlg.action == "archive":
                self.service.archive_task(task.id)
                from core.event_bus import event_bus
                event_bus.emit("entity_updated")
                self.load_data()
                return
            elif dlg.action == "delete_all":
                LinkService().delete_all_references_to("task", task.id)
            else:
                return
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Confirmar Exclusão", f"Tem certeza que deseja excluir a tarefa '{task.title}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            LinkService().delete_all_references_to("task", task.id)
            self.service.soft_delete_task(task.id)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.load_data()
        
    def load_data(self):
        try:
            _ = self.table.topLevelItemCount()
            _ = self.search_bar.text()
        except RuntimeError:
            return
            
        if self.show_archived:
            tasks = self.service.get_all_archived()
        else:
            tasks = self.service.get_all_active()
        self.current_tasks = tasks
        
        # Search filter — archived items bypass the filter
        query = self.search_bar.text().strip().lower()
        if query:
            filtered = []
            for t in tasks:
                if t.is_archived:
                    filtered.append(t)
                    continue
                match_id = query in str(t.id)
                match_title = query in (t.title or "").lower()
                match_period = False
                if t.start_date:
                    try:
                        import datetime
                        sd = datetime.datetime.fromisoformat(str(t.start_date))
                        match_period = match_period or query in sd.strftime("%d/%m/%Y").lower()
                    except: pass
                if t.due_date:
                    try:
                        import datetime
                        dd = datetime.datetime.fromisoformat(str(t.due_date))
                        match_period = match_period or query in dd.strftime("%d/%m/%Y").lower()
                    except: pass
                if match_id or match_title or match_period:
                    filtered.append(t)
            tasks = filtered
        
        # Desligar ordenação para não bagunçar a inserção
        self.table.setSortingEnabled(False)
        
        # Sort manually by position initially
        tasks = sorted(tasks, key=lambda t: t.position if t.position is not None else 0.0)
        
        # ADR-005 workaround: remove delegate AND freeze updates during entire population
        from gui.components.badge_delegate import BadgeDelegate
        old_delegate = self.table.itemDelegateForColumn(2)
        self.table.setItemDelegateForColumn(2, None)
        
        self.table.setUpdatesEnabled(False)
        try:
            self.table.clear()
            
            main_tasks = [t for t in tasks if not getattr(t, 'parent_task_id', None)]
            subtasks_by_parent = {}
            for t in tasks:
                pid = getattr(t, 'parent_task_id', None)
                if pid is not None:
                    subtasks_by_parent.setdefault(pid, []).append(t)
                    
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
                    from PySide6.QtGui import QColor, QBrush
                    if depth >= 2:
                        item.setForeground(1, QBrush(QColor("#b06ab3")))
                        bg = QColor(176, 106, 179, 22)
                    else:
                        item.setForeground(1, QBrush(QColor("#e67e22")))
                        bg = QColor(230, 126, 34, 18)
                    for _c in range(self.table.columnCount()):
                        item.setBackground(_c, QBrush(bg))

                item.setText(2, format_status(t.status, t.is_archived))
                item.setTextAlignment(2, Qt.AlignCenter)
                
                proj_name = self.projects_cache.get(t.project_id, "-")
                item.setText(3, proj_name)
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
                
                for sub_t in subtasks_by_parent.get(t.id, []):
                    create_tree_item(sub_t, item, depth + 1)
                
                return item

            for t in main_tasks:
                create_tree_item(t, self.table, 0)
                
        finally:
            # Restore delegate and updates BEFORE expandAll
            self.table.setItemDelegateForColumn(2, old_delegate)
            self.table.setUpdatesEnabled(True)

        from gui.components.drag_drop_tree_qt import fit_branch_arrows
        fit_branch_arrows(self.table)
        self.table.expandAll()
