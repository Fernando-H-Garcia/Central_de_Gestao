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
        self.project_alarm_tabs = QTabWidget()
        self.project_alarm_tabs.setStyleSheet(self._nested_tab_style())
        # Cada projeto com alarmes vira uma sub-aba aqui
        layout_alarmes.addWidget(self.project_alarm_tabs, stretch=1)
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
        
        self.project_event_tabs = QTabWidget()
        self.project_event_tabs.setStyleSheet(self._nested_tab_style())
        # Cada projeto com eventos vira uma sub-aba aqui
        layout_eventos.addWidget(self.project_event_tabs, stretch=1)
        self.agenda_tabs.addTab(tab_eventos, "Eventos")
        
        main_layout.addWidget(self.agenda_tabs, stretch=1)

    def _nested_tab_style(self):
        return """
            QTabWidget::pane { border: 1px solid #2a2a3f; border-top: none; }
            QTabBar::tab {
                background: #14142a;
                color: #888;
                padding: 8px 18px;
                border: 1px solid #2a2a3f;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected { background: #2a2a3f; color: #fff; }
            QTabBar::tab:hover:!selected { color: #d8d8f0; }
        """
        
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


    def _project_active(self, project_repo, pid):
        """Retorna True apenas se o projeto existe e não está arquivado/excluído."""
        if not pid:
            return True
        p = project_repo.get_by_id(pid)
        if p is None:
            return False
        return not (getattr(p, "is_archived", False) or getattr(p, "deleted_at", None) is not None)

    def load_data(self):
        try:
            from services.project_service import ProjectService
            from services.task_service import TaskService
            from services.alert_service import AlertService

            project_repo = ProjectService().project_repo
            task_repo = TaskService().task_repo

            # ── Eventos: agrupa por projeto → sub-aba em Eventos ──
            events = self.service.list_active()
            event_groups = {}
            for ev in events:
                pid = ev.project_id if ev.project_id else 0
                # Pula eventos de projetos excluídos/arquivados (mesma regra do widget)
                if not self._project_active(project_repo, pid):
                    continue
                event_groups.setdefault(pid, []).append(ev)
            self._rebuild_project_tabs(
                self.project_event_tabs, event_groups, project_repo, kind="events",
                task_repo=task_repo,
            )

            # ── Alarmes: agrupa por projeto → sub-aba em Alarmes ──
            alert_service = AlertService()
            all_alarms = [a for a in alert_service.alert_repo.get_all(include_archived=False, include_deleted=False) if a.status in ('pending', 'overdue')]
            alarm_groups = {}
            for al in all_alarms:
                pid = 0
                if al.entity_type == "task":
                    task = task_repo.get_by_id(al.entity_id)
                    # Pula alarmes de tarefas excluídas/arquivadas ou de projetos inativos
                    if not task or getattr(task, "is_archived", False) or getattr(task, "deleted_at", None) is not None:
                        continue
                    pid = task.project_id if task.project_id else 0
                    if not self._project_active(project_repo, pid):
                        continue
                elif al.entity_type == "project":
                    pid = al.entity_id
                    if not self._project_active(project_repo, pid):
                        continue
                alarm_groups.setdefault(pid, []).append(al)
            self._rebuild_project_tabs(
                self.project_alarm_tabs, alarm_groups, project_repo, kind="alarms",
                task_repo=task_repo,
            )
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

    def _rebuild_project_tabs(self, project_tabs, groups, project_repo, kind, **kw):
        """Reconstrói as sub-abas de projeto (uma por projeto) para alarmes ou eventos."""
        from PySide6.QtWidgets import QTabWidget
        
        # Ordena projetos por nome (Sem Projeto por último)
        proj_name = {}
        for pid in groups:
            if pid == 0:
                proj_name[pid] = "Sem Projeto"
            else:
                p = project_repo.get_by_id(pid)
                proj_name[pid] = p.name if p else f"Projeto {pid}"
        sorted_pids = sorted(proj_name.keys(), key=lambda pid: (proj_name[pid].lower() == "sem projeto", proj_name[pid].lower()))
        
        # Remove tabs antigos
        while project_tabs.count():
            w = project_tabs.widget(0)
            project_tabs.removeTab(0)
            if w is not None:
                w.deleteLater()
        
        from gui.components.alarm_cards_qt import AlarmCardsWidget
        from gui.components.agenda_tree_qt import AgendaTreeWidget
        
        for pid in sorted_pids:
            if kind == "alarms":
                widget = AlarmCardsWidget(
                    grouping="date",
                    filter_project_id=pid,
                    main_window=self.window(),
                    parent=self,
                )
                widget.populate(groups[pid])
            else:
                widget = AgendaTreeWidget(
                    grouping="date",
                    filter_project_id=pid,
                    main_window=self.window(),
                    parent=self,
                )
                widget.populate(groups[pid], project_repo, kw["task_repo"])
            title = f"{proj_name[pid]}{' (' + str(len(groups[pid])) + ')'}"
            project_tabs.addTab(widget, title)
