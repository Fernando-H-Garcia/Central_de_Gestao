from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMenu, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSettings
from gui.components.drag_drop_table_qt import DragDropTableWidget
from services.idea_service import IdeaService
from services.project_service import ProjectService
from gui.theme import get_status_color, get_energy_color, format_status
from PySide6.QtGui import QAction
from core.event_bus import event_bus

class IdeasQt(QWidget):
    def __init__(self, project_id=None, task_id=None):
        super().__init__()
        self.service = IdeaService()
        self.project_service = ProjectService()
        self.project_id = project_id
        self.task_id = task_id
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
        self.header = QLabel("💡 Ideias")
        self.header.setObjectName("header")
        header_layout.addWidget(self.header)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filtrar ideias...")
        self.search_bar.setStyleSheet("padding: 5px; border-radius: 5px; background-color: #13131f; color: white; border: 1px solid #2a2a3f; max-width: 250px;")
        self.search_bar.textChanged.connect(self.load_data)
        header_layout.addWidget(self.search_bar)
        
        header_layout.addStretch()
        
        self.btn_archived = QPushButton("📦 Arquivados: OFF")
        self.btn_archived.setObjectName("secondary")
        self.btn_archived.setCheckable(True)
        self.btn_archived.clicked.connect(self.toggle_archived)
        header_layout.addWidget(self.btn_archived)
        
        self.btn_new = QPushButton("💡 + Nova Ideia")
        self.btn_new.setObjectName("primary")
        self.btn_new.clicked.connect(self.open_new_dialog)
        header_layout.addWidget(self.btn_new)
        
        main_layout.addLayout(header_layout)
        
        self._snapshot_cb = lambda _: self.load_data()
        event_bus.subscribe("snapshot_updated", self._snapshot_cb)
        self.destroyed.connect(self._cleanup_snapshot)
        
        # Table Area
        self.table = DragDropTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Título", "Categoria", "Status", "Prioridade"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.itemDoubleClicked.connect(self.open_idea_detail)
        
        self.table.row_moved.connect(self.handle_row_moved)
        self.table.horizontalHeader().sectionClicked.connect(self.handle_header_click)
        
        # Context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.table.setAlternatingRowColors(True)
        from gui.components.badge_delegate import BadgeDelegate
        self.table.setItemDelegateForColumn(3, BadgeDelegate("status", parent=self.table))
        self.table.setItemDelegateForColumn(4, BadgeDelegate("priority", parent=self.table))
        main_layout.addWidget(self.table, stretch=1)
        
    def open_new_dialog(self):
        from gui.dialogs_qt.idea_dialog_qt import IdeaDialogQt
        dialog = IdeaDialogQt(self, project_id=self.project_id, task_id=self.task_id, on_save=lambda data: self.handle_save(data, True, None))
        dialog.exec()
        
    def open_idea_detail(self, item):
        idea = self.table.item(item.row(), 0).data(Qt.UserRole)
        self._open_idea_dialog(idea)

    def edit_idea(self, idea):
        self._open_idea_dialog(idea)

    def _open_idea_dialog(self, idea):
        from gui.dialogs_qt.idea_dialog_qt import IdeaDialogQt
        dialog = IdeaDialogQt(self, idea=idea, on_save=lambda data: self.handle_save(data, False, idea))
        dialog.exec()
        
    def handle_save(self, data, is_new, original_idea):
        try:
            if is_new:
                self.service.create_idea(**data)
            else:
                idea_copy = type(original_idea)(**original_idea.__dict__)
                for k, v in data.items():
                    setattr(idea_copy, k, v)
                self.service.update_idea(idea_copy, original_idea)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar a ideia:\n{e}")
            return
            
        event_bus.emit("entity_updated")
        self.load_data()
        
    def _cleanup_snapshot(self):
        event_bus.unsubscribe("snapshot_updated", self._snapshot_cb)

    def toggle_archived(self):
        self.show_archived = self.btn_archived.isChecked()
        self.btn_archived.setText(f"📦 Arquivados: {'ON' if self.show_archived else 'OFF'}")
        self.load_data()
        
    def load_data(self):
        try:
            query = self.search_bar.text().lower()
        except RuntimeError:
            return
            
        if self.show_archived:
            ideas = self.service.idea_repo.get_all(include_archived=True, include_deleted=False)
        else:
            ideas = self.service.get_all_active()
            
        if self.project_id:
            ideas = [i for i in ideas if i.project_id == self.project_id]
        if self.task_id:
            ideas = [i for i in ideas if getattr(i, 'task_id', None) == self.task_id]
            
        # Filter by search query
        query = self.search_bar.text().lower()
        if query:
            ideas = [i for i in ideas if query in (i.title or "").lower() or query in (i.description or "").lower()]
            
        # Desligar ordenação para não bagunçar a inserção
        self.table.setSortingEnabled(False)
        
        # Sort manually by position initially
        ideas = sorted(ideas, key=lambda i: i.position if i.position is not None else 0.0)
        
        # Remove badge delegates during bulk populate to avoid Qt 6.6.x paint crash
        old_delegates = {}
        for col in (3, 4):
            old_delegates[col] = self.table.itemDelegateForColumn(col)
            self.table.setItemDelegateForColumn(col, None)
        
        self.table.setRowCount(len(ideas))
        for row, i in enumerate(ideas):
            
            id_item = QTableWidgetItem(f"#{i.id}")
            id_item.setData(Qt.UserRole, i)
            title_item = QTableWidgetItem(i.title or "Sem título")
            cat_item = QTableWidgetItem(i.category or "Geral")
            status_item = QTableWidgetItem(format_status(i.status or "Pendente", getattr(i, 'is_archived', False)))
            prio_item = QTableWidgetItem(i.priority or "Média")
            
            # Styling colors (handled by BadgeDelegate)
            
            self.table.setItem(row, 0, id_item)
            self.table.setItem(row, 1, title_item)
            self.table.setItem(row, 2, cat_item)
            self.table.setItem(row, 3, status_item)
            self.table.setItem(row, 4, prio_item)
            
        # Restore badge delegates
        for col, delg in old_delegates.items():
            self.table.setItemDelegateForColumn(col, delg)
            
        col = self.settings.value("ideas_sort_column", -1, type=int)
        if col >= 0:
            order_val = self.settings.value("ideas_sort_order", Qt.AscendingOrder.value, type=int)
            order = Qt.SortOrder(order_val)
            self.table.setSortingEnabled(True)
            self.table.sortItems(col, order)
            self.table.setSortingEnabled(False)
            
            self.table.horizontalHeader().setSortIndicator(col, order)
            self.table.horizontalHeader().setSortIndicatorShown(True)
        else:
            self.table.horizontalHeader().setSortIndicatorShown(False)

    def on_header_clicked(self, logical_index):
        current_order = self.table.horizontalHeader().sortIndicatorOrder()
        self.settings.setValue("ideas_sort_column", logical_index)
        self.settings.setValue("ideas_sort_order", current_order)
        self.load_data()

    def restore_sort_order(self):
        pass

    def handle_header_click(self, logical_index):
        current_order = self.table.horizontalHeader().sortIndicatorOrder()
        self.settings.setValue("ideas_sort_column", logical_index)
        self.settings.setValue("ideas_sort_order", current_order)
        self.load_data()

    def handle_row_moved(self, idea_id, target_row):
        visual_ideas = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                i = item.data(Qt.UserRole)
                if i:
                    visual_ideas.append(i)
                    
        idea = next((i for i in visual_ideas if i.id == idea_id), None)
        if not idea: return
        
        source_row = visual_ideas.index(idea)
        visual_ideas.remove(idea)
        
        if source_row < target_row:
            target_row -= 1
            
        visual_ideas.insert(target_row, idea)
        
        # Agora salvamos essa nova ordem como a oficial manual
        for row, i in enumerate(visual_ideas):
            new_pos = float(row * 100)
            i.position = new_pos
            self.service.update_idea_position(i.id, new_pos)
            
        # Limpar organização de coluna pois agora é manual
        self.settings.remove("ideas_sort_column")
        self.settings.remove("ideas_sort_order")
        self.table.horizontalHeader().setSortIndicatorShown(False)
        
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.load_data()

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        idea = self.table.item(item.row(), 0).data(Qt.UserRole)
        
        menu = QMenu(self)
        
        edit_action = QAction("✏️ Editar Ideia", self)
        edit_action.triggered.connect(lambda: self.edit_idea(idea))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        promote_proj_action = QAction("🚀 Promover para Projeto", self)
        promote_proj_action.triggered.connect(lambda: self.open_promote_project(idea))
        menu.addAction(promote_proj_action)
        
        promote_task_action = QAction("📋 Promover para Tarefa", self)
        promote_task_action.triggered.connect(lambda: self.open_promote_task(idea))
        menu.addAction(promote_task_action)
        
        menu.addSeparator()
        
        from gui.theme import create_color_icon
        
        prio_menu = menu.addMenu("Alterar Prioridade")
        for p in ["Baixa", "Média", "Alta", "Crítica"]:
            action = QAction(p, self)
            from gui.theme import get_energy_color
            action.setIcon(create_color_icon(get_energy_color(p)))
            action.triggered.connect(lambda ch, prio=p: self.change_priority(idea, prio))
            prio_menu.addAction(action)
            
        status_menu = menu.addMenu("Alterar Status")
        for s in ["Pendente", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"]:
            action = QAction(s, self)
            from gui.theme import get_status_color
            action.setIcon(create_color_icon(get_status_color(s)))
            action.triggered.connect(lambda ch, st=s: self.change_status(idea, st))
            status_menu.addAction(action)
            
        menu.addSeparator()
        
        del_action = QAction("🗑️ Excluir", self)
        del_action.triggered.connect(lambda: self.delete_idea(idea))
        menu.addAction(del_action)
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))
        
    def change_priority(self, idea, prio):
        orig = type(idea)(**idea.__dict__)
        idea.priority = prio
        self.service.update_idea(idea, orig)
        event_bus.emit("entity_updated")
        self.load_data()
        
    def change_status(self, idea, st):
        orig = type(idea)(**idea.__dict__)
        idea.status = st
        self.service.update_idea(idea, orig)
        event_bus.emit("entity_updated")
        self.load_data()
        
    def delete_idea(self, idea):
        reply = QMessageBox.question(self, "Confirmar", f"Tem certeza que deseja excluir '{idea.title}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.service.idea_repo.delete(idea.id)
            event_bus.emit("entity_updated")
            self.load_data()

    def open_promote_project(self, idea):
        from gui.dialogs_qt.promote_idea_dialog_qt import PromoteIdeaDialogQt
        def handle_promote(data):
            self.service.promote_to_project(
                idea_id=idea.id,
                project_title=data["title"],
                description_text=data["description"],
                copy_tags=data["copy_tags"],
                copy_attachments=data["copy_tags"],
                link_idea=data["keep_linked"]
            )
            event_bus.emit("entity_updated")
            self.load_data()
            QMessageBox.information(self, "Sucesso", "Projeto criado a partir da ideia com sucesso!")
            
        dialog = PromoteIdeaDialogQt(self, idea=idea, default_type="project", on_promote=handle_promote)
        dialog.exec()

    def open_promote_task(self, idea):
        from gui.dialogs_qt.promote_idea_dialog_qt import PromoteIdeaDialogQt
        def handle_promote(data):
            self.service.promote_to_task(
                idea_id=idea.id,
                task_title=data["title"],
                description_text=data["description"],
                copy_tags=data["copy_tags"],
                copy_attachments=data["copy_tags"],
                link_idea=data["keep_linked"],
                project_id=data["project_id"]
            )
            event_bus.emit("entity_updated")
            self.load_data()
            QMessageBox.information(self, "Sucesso", "Tarefa criada a partir da ideia com sucesso!")
            
        dialog = PromoteIdeaDialogQt(self, idea=idea, default_type="task", on_promote=handle_promote)
        dialog.exec()
