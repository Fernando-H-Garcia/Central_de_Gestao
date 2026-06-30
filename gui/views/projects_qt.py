from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, Signal
from services.project_service import ProjectService
from gui.theme import get_status_color, get_energy_color, FONT_SUBTITLE, FONT_BODY, FONT_CAPTION
from gui.components.page_header import PageHeader

class ClickableFrame(QFrame):
    doubleClicked = Signal()
    rightClicked = Signal(object) # pass event
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()
            super().mouseDoubleClickEvent(event)
            
    def contextMenuEvent(self, event):
        self.rightClicked.emit(event)
        super().contextMenuEvent(event)

class ProjectsQt(QWidget):
    open_project_360 = Signal(int)

    def __init__(self):
        super().__init__()
        self.service = ProjectService()
        self.show_archived = False
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        self.header = PageHeader("Projetos")
        
        self.btn_archived = QPushButton("📦 Arquivados: OFF")
        self.btn_archived.setObjectName("secondary")
        self.btn_archived.setCheckable(True)
        self.btn_archived.clicked.connect(self.toggle_archived)
        self.header.add_button(self.btn_archived)
        
        self.btn_new = QPushButton("📁 + Novo Projeto")
        self.btn_new.setObjectName("secondary")
        self.btn_new.clicked.connect(self.open_new_dialog)
        self.header.add_button(self.btn_new)
        main_layout.addWidget(self.header)
        
        from core.event_bus import event_bus
        event_bus.subscribe("snapshot_updated", self.safe_load_data)
        event_bus.subscribe("entity_updated", self.safe_load_data)
        self.destroyed.connect(self._cleanup_snapshot)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background-color: transparent;")
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.scroll.setWidget(self.grid_widget)
        
        main_layout.addWidget(self.scroll, stretch=1)

    def _cleanup_snapshot(self):
        from core.event_bus import event_bus
        event_bus.unsubscribe("snapshot_updated", self.safe_load_data)

    def safe_load_data(self, _=None):
        try:
            self.load_data()
        except RuntimeError:
            pass
        
    def open_new_dialog(self):
        from gui.dialogs_qt.project_dialog_qt import ProjectDialogQt
        dialog = ProjectDialogQt(self, on_save=self.handle_save)
        dialog.exec()
        
    def open_edit_dialog(self, project):
        from gui.dialogs_qt.project_dialog_qt import ProjectDialogQt
        dialog = ProjectDialogQt(self, project=project, on_save=self.handle_save)
        dialog.exec()
        
    def handle_save(self, project, is_new, original_project=None):
        if is_new:
            self.service.create_project(
                name=project.name, 
                objective=project.objective, 
                priority=project.priority, 
                due_date=project.due_date, 
                alert_date=project.alert_date, 
                alert_message=project.alert_message
            )
        else:
            self.service.update_project(project, original_project)
        from core.event_bus import event_bus
        event_bus.emit("entity_updated")
        self.load_data()
        
    def toggle_archived(self):
        self.show_archived = self.btn_archived.isChecked()
        self.btn_archived.setText(f"📦 Arquivados: {'ON' if self.show_archived else 'OFF'}")
        self.load_data()

    def load_data(self):
        if self.show_archived:
            projects = self.service.get_all_archived()
        else:
            projects = self.service.get_all_active()
        
        # Clear layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        row, col = 0, 0
        from PySide6.QtWidgets import QMenu, QMessageBox
        
        for p in projects:
            card = ClickableFrame()
            card.setStyleSheet("background-color: #1c1c2e; border-radius: 10px;")
            card.setFixedSize(320, 160)
            card.doubleClicked.connect(lambda pid=p.id: self.open_project_360.emit(pid))
            card.rightClicked.connect(lambda ev, proj=p: self.show_context_menu(ev, proj))
            card.setCursor(Qt.PointingHandCursor)
            
            card_layout = QVBoxLayout(card)
            
            lbl_name = QLabel(p.name)
            lbl_name.setStyleSheet(f"font-size: {FONT_SUBTITLE}px; font-weight: bold; color: #fff;")
            lbl_name.setWordWrap(True)
            card_layout.addWidget(lbl_name)
            
            lbl_desc = QLabel(p.objective or "Sem descrição")
            lbl_desc.setStyleSheet(f"color: #888; font-size: {FONT_BODY}px;")
            lbl_desc.setWordWrap(True)
            card_layout.addWidget(lbl_desc)
            
            card_layout.addStretch()
            
            info_layout = QHBoxLayout()
            
            lbl_status = QLabel(p.status)
            lbl_status.setStyleSheet(f"font-size: {FONT_CAPTION}px; font-weight: bold; color: {get_status_color(p.status)}; background-color: #2a2a3f; padding: 2px 6px; border-radius: 3px;")
            info_layout.addWidget(lbl_status)
            
            prio_val = p.priority if hasattr(p, 'priority') and p.priority else "-"
            lbl_prio = QLabel(prio_val)
            lbl_prio.setStyleSheet(f"font-size: {FONT_CAPTION}px; font-weight: bold; color: {get_energy_color(prio_val)}; background-color: #2a2a3f; padding: 2px 6px; border-radius: 3px;")
            info_layout.addWidget(lbl_prio)
            
            info_layout.addStretch()
            
            due = "-"
            if hasattr(p, 'due_date') and p.due_date:
                try:
                    import datetime
                    dt = datetime.datetime.fromisoformat(str(p.due_date))
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
                    due = str(p.due_date).split()[0]
                    
            lbl_due = QLabel(f"📅 Prazo: {due}")
            lbl_due.setStyleSheet(f"font-size: {FONT_CAPTION}px; font-weight: bold; color: #ccc;")
            info_layout.addWidget(lbl_due)
            
            card_layout.addLayout(info_layout)
            
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col > 2:
                col = 0
                row += 1
                
    def show_context_menu(self, event, project):
        from PySide6.QtWidgets import QMenu, QMessageBox
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1c1c2e; color: white; border: 1px solid #2a2a3f; } QMenu::item:selected { background-color: #2d2d55; }")
        
        action_open = menu.addAction("🗂️ Abrir")
        action_edit = menu.addAction("✏️ Editar")
        menu.addSeparator()
        action_archive = menu.addAction("📦 Desarquivar" if getattr(project, "is_archived", False) else "📦 Arquivar")
        menu.addSeparator()
        action_delete = menu.addAction("🗑️ Excluir")
        
        action = menu.exec(event.globalPos())
        if action == action_open:
            self.open_project_360.emit(project.id)
        elif action == action_edit:
            self.open_edit_dialog(project)
        elif action == action_archive:
            if getattr(project, "is_archived", False):
                self.service.restore_project(project.id)
            else:
                self.service.archive_project(project.id)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")
            self.load_data()
        elif action == action_delete:
            from services.link_service import LinkService
            refs = LinkService().find_references_to_entity("project", project.id)
            if refs:
                from gui.dialogs_qt.reference_warning_dialog_qt import ReferenceWarningDialog
                dlg = ReferenceWarningDialog("projeto", project.name, refs, self, show_archive=True)
                dlg.exec()
                if dlg.action == "archive":
                    self.service.archive_project(project.id)
                    from core.event_bus import event_bus
                    event_bus.emit("entity_updated")
                    self.load_data()
                    return
                elif dlg.action == "delete_all":
                    LinkService().delete_all_references_to("project", project.id)
                else:
                    return
            reply = QMessageBox.question(self, "Confirmação", "Deseja realmente excluir este projeto e todas as suas tarefas?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                LinkService().delete_all_references_to("project", project.id)
                self.service.soft_delete_project(project.id)
                from core.event_bus import event_bus
                event_bus.emit("entity_updated")
                self.load_data()
