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
        self._window_visible_logged = False
        self._paint_logged = False
        
        self.setup_ui()
        self.load_stylesheet()
        
        from core.event_bus import event_bus
        event_bus.subscribe("navigate_to", self._on_global_navigate)

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
        self._nav_history.append(self.stacked_widget.currentWidget())
        for i, btn in self.nav_buttons.items():
            btn.setChecked(i == idx)
        self.stacked_widget.setCurrentIndex(idx)
        
    def _restore_nav_button(self, idx):
        nav_items = {
            0: "Monitor",
            1: "Projetos",
            2: "Resumo Atividades",
            3: "Agenda Geral",
            4: "Documentação"
        }
        item_name = nav_items.get(idx)
        if idx in self.nav_buttons:
            self.nav_buttons[idx].setChecked(True)

    def show_project_360(self, project_id, origin_widget=None):
        from gui.views.project_360_qt import Project360Qt
        
        self._nav_history.append(self.stacked_widget.currentWidget())
        
        # Deselect sidebar buttons since we are in a sub-view
        self.btn_group.setExclusive(False)
        for btn in self.btn_group.buttons():
            btn.setChecked(False)
        self.btn_group.setExclusive(True)
        
        # Check if project 360 is already open, if not create it
        if hasattr(self, 'project_360_view'):
            self.stacked_widget.removeWidget(self.project_360_view)
            self.project_360_view.deleteLater()
            
        self.project_360_view = Project360Qt(project_id)
        
        self.project_360_view.go_back.connect(self._navigate_back)
        self.project_360_view.open_task_detail_signal.connect(lambda tid: self.show_task_detail(tid, origin_widget=self.project_360_view))
        
        self.stacked_widget.addWidget(self.project_360_view)
        self.stacked_widget.setCurrentWidget(self.project_360_view)
        
    def show_task_detail(self, task_id, origin_widget=None):
        from gui.views.task_detail_qt import TaskDetailQt
        
        self._nav_history.append(self.stacked_widget.currentWidget())
        
        # Deselect sidebar buttons since we are in a sub-view
        self.btn_group.setExclusive(False)
        for btn in self.btn_group.buttons():
            btn.setChecked(False)
        self.btn_group.setExclusive(True)
        
        if hasattr(self, 'task_detail_view'):
            try:
                self.stacked_widget.removeWidget(self.task_detail_view)
                self.task_detail_view.deleteLater()
            except RuntimeError:
                pass
                
        self.task_detail_view = TaskDetailQt(task_id)
        
        self.task_detail_view.go_back.connect(self._navigate_back)
            
        self.stacked_widget.addWidget(self.task_detail_view)
        self.stacked_widget.setCurrentWidget(self.task_detail_view)
        
    def _navigate_back(self):
        while self._nav_history:
            prev_widget = self._nav_history.pop()
            idx = self.stacked_widget.indexOf(prev_widget)
            if idx >= 0:
                self.stacked_widget.setCurrentIndex(idx)
                if idx < 5:
                    self._restore_nav_button(idx)
                return

    def load_stylesheet(self):
        pass
