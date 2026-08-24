from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QFrame, QPushButton, QStackedWidget, QLabel, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPaintEvent
from gui.theme import FONT_TITLE, FONT_CAPTION

def _boot_log_append(msg: str):
    try:
        from config import LOGS_DIR
        from datetime import datetime
        p = LOGS_DIR / "boot.log"
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [BOOT] {msg}\n")
    except Exception:
        pass

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Central de Gestão")
        self.setMinimumSize(1000, 700)
        self._layout_fixed = False
        self._nav_history = []
        self._current_target = None
        self._project_views = {}
        self._task_views = {}
        self._window_visible_logged = False
        self._paint_logged = False
        
        self.setup_ui()
        self.load_stylesheet()
        self._setup_global_alarm_timer()
        
        from core.event_bus import event_bus
        event_bus.subscribe("navigate_to", self._on_global_navigate)

    def _setup_global_alarm_timer(self):
        """Global alarm monitor: fires regardless of which screen is visible."""
        self._global_alarm_popup_open = False
        self._global_alarm_stuck_since = None
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, self._check_global_alarms)
        self._global_alarm_timer = QTimer(self)
        self._global_alarm_timer.timeout.connect(self._check_global_alarms)
        self._global_alarm_timer.start(10000)

    def _check_global_alarms(self):
        """Periodic global alarm check independent of the currently visible view."""
        if self._global_alarm_popup_open:
            import time
            if self._global_alarm_stuck_since is None:
                self._global_alarm_stuck_since = time.time()
            elif time.time() - self._global_alarm_stuck_since > 60:
                self._global_alarm_popup_open = False
                self._global_alarm_stuck_since = None
            return
        self._global_alarm_stuck_since = None
        try:
            from services.alert_service import AlertService
            from services.task_service import TaskService
            self._global_alarm_popup_open = True
            alert_service = AlertService()
            task_service = TaskService()
            alert_service.mark_overdue_alerts()
            alarms = alert_service.get_active_alarms_all(task_service)
            if not alarms:
                return

            task_map = {}
            try:
                from models.task import Task
                tasks = task_service.get_all_active()
                task_map = {t.id: t for t in tasks}
            except Exception:
                task_map = {}

            for alarm in alarms:
                t = task_map.get(alarm.entity_id)
                alarm._task_title = t.title if t else f"Tarefa #{alarm.entity_id}"

            from gui.dialogs_qt.alarm_popup_qt import AlarmPopupQt
            popup = AlarmPopupQt(alarms, task_map, parent=self)
            popup.open_task_requested.connect(self.show_task_detail)
            popup.exec()
        except Exception:
            import traceback, os
            from config import LOGS_DIR
            log_path = os.path.join(LOGS_DIR, "app_errors.log")
            try:
                with open(log_path, "a") as f:
                    f.write("\nCRASH IN _check_global_alarms:\n")
                    traceback.print_exc(file=f)
            except Exception:
                pass
        finally:
            self._global_alarm_popup_open = False
            self._global_alarm_stuck_since = None

    def showEvent(self, event):
        super().showEvent(event)
        if not self._layout_fixed:
            QTimer.singleShot(0, self._fix_layout)
        if not self._window_visible_logged and self.isVisible():
            self._window_visible_logged = True
            _boot_log_append(
                f"MainWindow showEvent "
                f"isVisible={self.isVisible()} "
                f"isMinimized={self.isMinimized()} "
                f"isMaximized={self.isMaximized()}"
            )

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        if not self._paint_logged:
            self._paint_logged = True
            _boot_log_append("primeiro paint recebido")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._layout_fixed and self.isVisible():
            self._layout_fixed = True
            QTimer.singleShot(0, self._fix_layout)

    def _fix_layout(self):
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        cw = self.centralWidget()
        if cw:
            cw.layout().invalidate()
            cw.layout().activate()
        for i in range(self.stacked_widget.count()):
            w = self.stacked_widget.widget(i)
            if w:
                w.updateGeometry()
        self.stacked_widget.updateGeometry()
        self.updateGeometry()
        QApplication.processEvents()
        
    def _on_global_navigate(self, payload: dict):
        e_type = payload.get("type")
        e_id = payload.get("id")
        if not e_id: return
        if e_type == "project":
            self.show_project_360(e_id)
        elif e_type == "task":
            self.show_task_detail(e_id)
        elif e_type in ("wiki", "knowledge_page"):
            self.change_page(4)  # Switch to "Documentação" tab
            # WikiQt catches the same navigate_to event and opens the page
        elif e_type == "idea":
            from services.idea_service import IdeaService
            idea = IdeaService().get_by_id(e_id)
            if idea:
                if idea.project_id:
                    self.show_project_360(idea.project_id)
                elif idea.task_id:
                    self.show_task_detail(idea.task_id)
        
    def setup_ui(self):
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Title area with icon
        title_frame = QFrame()
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(16, 24, 16, 16)
        title_layout.setSpacing(4)

        icon_label = QLabel("⚙️ Central de Gestão")
        icon_label.setStyleSheet(f"font-size: {FONT_TITLE}px; font-weight: bold; padding: 0px; letter-spacing: 0.5px;")
        title_layout.addWidget(icon_label)

        subtitle = QLabel("Sistema de Gestão de Projetos Integrada")
        subtitle.setStyleSheet(f"color: #666666; font-size: {FONT_CAPTION}px; padding: 0px;")
        title_layout.addWidget(subtitle)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: #2a2a3f; margin: 0 16px;")
        sidebar_layout.addWidget(title_frame)
        sidebar_layout.addWidget(sep)

        # Navigation Buttons
        nav_area = QFrame()
        nav_layout = QVBoxLayout(nav_area)
        nav_layout.setContentsMargins(8, 12, 8, 12)
        nav_layout.setSpacing(2)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.nav_buttons = {}
        nav_defs = [
            ("📊", "Monitor"),
            ("📁", "Projetos"),
            ("📋", "Resumo das Atividades"),
            ("📅", "Agenda Geral"),
            ("📖", "Documentação"),
        ]

        for i, (emoji, item) in enumerate(nav_defs):
            btn = QPushButton(f"  {emoji}  {item}")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda *args, idx=i: self.change_page(idx))
            self.nav_buttons[i] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        sidebar_layout.addWidget(nav_area, stretch=1)

        # Bottom info
        bottom_frame = QFrame()
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(16, 8, 16, 12)
        bottom_layout.setSpacing(2)
        version_lbl = QLabel("v0.8")
        version_lbl.setStyleSheet(f"color: #555555; font-size: {FONT_CAPTION}px;")
        bottom_layout.addWidget(version_lbl)
        sidebar_layout.addWidget(bottom_frame)
        
        # Main content area
        self.stacked_widget = QStackedWidget()
        
        from gui.views.workbench_qt import WorkbenchQt
        from gui.views.wiki_qt import WikiQt
        from gui.views.projects_qt import ProjectsQt
        from gui.views.agenda_qt import AgendaQt
        from gui.views.activity_summary_qt import ActivitySummaryQt
        
        nav_items = ["Monitor", "Projetos", "Resumo das Atividades", "Agenda Geral", "Documentação"]
        
        # Add placeholders and actual views
        for i, item in enumerate(nav_items):
            if item == "Monitor":
                page = WorkbenchQt()
            elif item == "Projetos":
                page = ProjectsQt()
            elif item == "Resumo das Atividades":
                page = ActivitySummaryQt()
                page.go_back.connect(self._navigate_back)
            elif item == "Agenda Geral":
                page = AgendaQt()
            elif item == "Documentação":
                page = WikiQt()
            else:
                page = QWidget()
                
            self.stacked_widget.addWidget(page)
            
            # If the page emits open_task_detail_signal, connect it
            if hasattr(page, "open_task_detail_signal"):
                # Notice we capture 'page' via pw=page to avoid late-binding closure issues!
                page.open_task_detail_signal.connect(lambda tid, pw=page: self.show_task_detail(tid, origin_widget=pw))
            
            if item == "Projetos":
                page.open_project_360.connect(self.show_project_360)
                
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stacked_widget, stretch=1)
        
    def change_page(self, idx):
        self._push_target(self._current_target)
        self._show_page(idx)
        
    def _push_target(self, target):
        if target is None:
            return
        if self._nav_history and self._nav_history[-1] == target:
            return
        self._nav_history.append(target)

    def _show_page(self, idx):
        self._current_target = ("page", idx)
        for i, btn in self.nav_buttons.items():
            btn.setChecked(i == idx)
        self.stacked_widget.setCurrentIndex(idx)

    def _deselect_nav_buttons(self):
        self.btn_group.setExclusive(False)
        for btn in self.btn_group.buttons():
            btn.setChecked(False)
        self.btn_group.setExclusive(True)

    def _show_project(self, project_id):
        from gui.views.project_360_qt import Project360Qt

        target = ("project", project_id)
        view = self._project_views.get(project_id)
        if view is None:
            view = Project360Qt(project_id)
            view.go_back.connect(self._navigate_back)
            view.open_task_detail_signal.connect(lambda tid: self.show_task_detail(tid, origin_widget=view))
            self.stacked_widget.addWidget(view)
            self._project_views[project_id] = view

        self._current_target = target
        self._deselect_nav_buttons()
        self.stacked_widget.setCurrentWidget(view)

    def show_project_360(self, project_id, origin_widget=None):
        if self._current_target != ("project", project_id):
            self._push_target(self._current_target)
        self._show_project(project_id)

    def _show_task(self, task_id):
        from gui.views.task_detail_qt import TaskDetailQt

        target = ("task", task_id)
        view = self._task_views.get(task_id)
        if view is None:
            view = TaskDetailQt(task_id)
            if view.task is None:
                return
            view.go_back.connect(self._navigate_back)
            self.stacked_widget.addWidget(view)
            self._task_views[task_id] = view

        self._current_target = target
        self._deselect_nav_buttons()
        self.stacked_widget.setCurrentWidget(view)

    def show_task_detail(self, task_id, origin_widget=None):
        if self._current_target != ("task", task_id):
            self._push_target(self._current_target)
        self._show_task(task_id)

    def _navigate_back(self):
        current = self._current_target
        while self._nav_history:
            target = self._nav_history.pop()
            if target == current:
                continue
            kind = target[0]
            if kind == "page":
                self._show_page(target[1])
            elif kind == "project":
                self._show_project(target[1])
            elif kind == "task":
                self._show_task(target[1])
            else:
                continue
            return

    def load_stylesheet(self):
        pass
