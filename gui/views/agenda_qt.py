from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt
from services.event_service import EventService
from gui.components.page_header import PageHeader
import datetime

class AgendaQt(QWidget):
    def __init__(self):
        super().__init__()
        self.service = EventService()
        self.setup_ui()
        self.load_data()
        
        from core.event_bus import event_bus
        event_bus.subscribe("snapshot_updated", self.safe_load_data)
        event_bus.subscribe("entity_updated", self.safe_load_data)
        self.destroyed.connect(self._cleanup_snapshot)

    def _cleanup_snapshot(self):
        from core.event_bus import event_bus
        event_bus.unsubscribe("snapshot_updated", self.safe_load_data)
        event_bus.unsubscribe("entity_updated", self.safe_load_data)

    def safe_load_data(self, _=None):
        try:
            self.load_data()
        except RuntimeError:
            pass

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        self.header = PageHeader("Agenda Geral")
        main_layout.addWidget(self.header)
        
        from PySide6.QtWidgets import QTabWidget
        self.agenda_tabs = QTabWidget()
        self.agenda_tabs.setStyleSheet("""
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
        
        # Sub-tab Alarmes
        tab_alarmes = QWidget()
        layout_alarmes = QVBoxLayout(tab_alarmes)
        from gui.components.alarm_cards_qt import AlarmCardsWidget
        self.tree_alarms = AlarmCardsWidget(grouping="project", main_window=self.window(), parent=self)
        layout_alarmes.addWidget(self.tree_alarms, stretch=1)
        self.agenda_tabs.addTab(tab_alarmes, "Alarmes")

        # Sub-tab Eventos
        tab_eventos = QWidget()
        layout_eventos = QVBoxLayout(tab_eventos)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_new = QPushButton("📅 + Novo Evento")
        self.btn_new.setObjectName("secondary")
        self.btn_new.clicked.connect(self.new_event)
        btn_layout.addWidget(self.btn_new)
        layout_eventos.addLayout(btn_layout)
        
        from gui.components.agenda_tree_qt import AgendaTreeWidget
        self.tree = AgendaTreeWidget(grouping="project", main_window=self.window(), parent=self)
        layout_eventos.addWidget(self.tree, stretch=1)
        self.agenda_tabs.addTab(tab_eventos, "Eventos")
        
        main_layout.addWidget(self.agenda_tabs, stretch=1)
        
    def new_event(self):
        try:
            from gui.dialogs_qt.event_dialog_qt import EventDialogQt
            dialog = EventDialogQt(None)
            if dialog.exec():
                self.load_data()
        except Exception as e:
            import traceback
            import os
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN NEW_EVENT (agenda_qt):\n")
                    traceback.print_exc(file=f)
            except:
                pass


    def load_data(self):
        try:
            events = self.service.list_active()
            from services.project_service import ProjectService
            from services.task_service import TaskService
            from services.alert_service import AlertService
            self.tree.populate(events, ProjectService().project_repo, TaskService().task_repo)
            
            # Load all active alarms for the general view
            alert_service = AlertService()
            all_alarms = [a for a in alert_service.alert_repo.get_all(include_archived=False, include_deleted=False) if a.status in ('pending', 'overdue')]
            self.tree_alarms.populate(all_alarms)
        except Exception as e:
            print("Erro ao carregar dados:", e)
            import traceback
            import os
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN AGENDA_QT LOAD_DATA:\n")
                    traceback.print_exc(file=f)
            except:
                pass
