from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QFrame, QTabWidget, QWidget, QLineEdit,
    QGridLayout, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QInputDialog, QMessageBox, QMenu, QTreeWidget, QTreeWidgetItem, QTextBrowser
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QSizePolicy
from gui.theme import get_status_color, get_energy_color, format_colored_label
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
            
        self.setup_ui()
        self.load_data()

        from PySide6.QtCore import QTimer
        self._alarm_timer = QTimer(self)
        self._alarm_timer.timeout.connect(self.load_agenda)
        self._alarm_timer.start(30000)

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
        
        btn_back = QPushButton("← Voltar")
        btn_back.setObjectName("secondary")
        btn_back.clicked.connect(self.go_back.emit)
        header_layout.addWidget(btn_back)
        
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
        
        self.tab_agenda = QWidget()
        self.setup_agenda_tab()
        self.tabs.addTab(self.tab_agenda, "Agenda")

        main_layout.addWidget(self.tabs)

        
    def setup_geral_tab(self):
        layout = QVBoxLayout(self.tab_geral)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Status:"), 0, 0)
        lbl_status = QLabel(self.task.status)
        lbl_status.setStyleSheet(f"color: {get_status_color(self.task.status)}; font-weight: bold;")
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
        
        # Add a visual label for logs
        lbl_logs = QLabel("Atividades / Logs:")
        lbl_logs.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_logs)
        
        # Toolbar
        toolbar = QHBoxLayout()
        btn_add = QPushButton("📝 + Nova Atividade")
        btn_add.setObjectName("secondary")
        btn_add.clicked.connect(self.add_activity)
        toolbar.addStretch()
        toolbar.addWidget(btn_add)
        layout.addLayout(toolbar)
        
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

    def _adjust_log_row(self, row, tb):
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        tb.document().setDocumentMargin(3)
        w = tb.viewport().width() - 6
        if w < 50:
            w = 400
        tb.document().setTextWidth(w)
        h = tb.document().size().height()
        self.tbl_logs.setRowHeight(row, max(int(h) + 10, 30))

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

    def load_data(self):
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
            "RESTORED": "RESTAURADO"
        }
        
        color_mapping = {
            "CRIADO": "#4caf50",
            "ATUALIZADO": "#2196f3",
            "MUDANÇA DE STATUS": "#ff9800",
            "COMENTÁRIO": "#e91e63"
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
            self.tbl_logs.setCellWidget(i, 2, tb)
            QTimer.singleShot(0, lambda r=i, t=tb: self._adjust_log_row(r, t))
            
        self.load_agenda()

    def setup_agenda_tab(self):
        layout = QVBoxLayout(self.tab_agenda)
        
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

        alarm_header = QHBoxLayout()
        alarm_header.addStretch()
        self.btn_new_alarm = QPushButton("🔔 + Novo Alarme")
        self.btn_new_alarm.setObjectName("secondary")
        self.btn_new_alarm.clicked.connect(self.new_alarm)
        alarm_header.addWidget(self.btn_new_alarm)
        layout_alarmes.addLayout(alarm_header)

        from gui.components.alarm_cards_qt import AlarmCardsWidget
        self.tree_alarms = AlarmCardsWidget(grouping="date", filter_project_id=self.task.project_id, highlight_task_id=self.task.id, main_window=self.window(), parent=self)
        layout_alarmes.addWidget(self.tree_alarms)
        self.agenda_tabs.addTab(tab_alarmes, "Alarmes")
        
        # Sub-tab Eventos
        tab_eventos = QWidget()
        layout_eventos = QVBoxLayout(tab_eventos)
        
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        self.btn_new_event = QPushButton("🔔 + Novo Evento (Alerta)")
        self.btn_new_event.setObjectName("secondary")
        self.btn_new_event.clicked.connect(self.new_agenda_event)
        header_layout.addWidget(self.btn_new_event)
        layout_eventos.addLayout(header_layout)
        
        from gui.components.agenda_tree_qt import AgendaTreeWidget
        self.tree_agenda = AgendaTreeWidget(grouping="date", filter_project_id=self.task.project_id, highlight_task_id=self.task.id, main_window=self.window(), parent=self)
        layout_eventos.addWidget(self.tree_agenda)
        self.agenda_tabs.addTab(tab_eventos, "Eventos")
        
        layout.addWidget(self.agenda_tabs)
        
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

        # Load Alarms
        try:
            from services.alert_service import AlertService
            alert_service = AlertService()
            task_ids = [t.id for t in self.service.get_all_active() if t.project_id == self.task.project_id]
            all_alarms = alert_service.alert_repo.get_all(include_archived=False, include_deleted=False)
            task_alarms = [a for a in all_alarms if a.entity_type == "task" and a.entity_id in task_ids and a.status in ('pending', 'overdue')]
            proj_alarms = [a for a in all_alarms if a.entity_type == "project" and a.entity_id == self.task.project_id and a.status in ('pending', 'overdue')]
            alarms = task_alarms + proj_alarms
            self.tree_alarms.populate(alarms)
        except Exception:
            import traceback
            traceback.print_exc()
