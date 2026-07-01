from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu, QMessageBox
)
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtCore import Qt
from gui.theme import GLOBAL_STYLE, BG_HOVER, FONT_CAPTION

class AgendaTreeWidget(QTreeWidget):
    def __init__(self, grouping="project", filter_project_id=None, filter_task_id=None, highlight_task_id=None, main_window=None, parent=None):
        super().__init__(parent)
        self.grouping = grouping # "project" or "date"
        self.filter_project_id = filter_project_id
        self.filter_task_id = filter_task_id
        self.highlight_task_id = highlight_task_id
        self.main_window = main_window
        self.main_view = parent
        
        self.setColumnCount(5)
        self.setHeaderLabels(["Data / Hora", "Título", "Descrição", "Tarefa", "Tipo"])
        self.setWordWrap(True)
        
        # Adjust column widths
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.setColumnWidth(1, 200)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        self.setTextElideMode(Qt.ElideNone)
        
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setIndentation(20)
        
        # Double click to open edit
        self.itemDoubleClicked.connect(self.handle_double_click)

    def populate(self, events, project_repo, task_repo):
        self.clear()
        
        # Sort events by date
        sorted_events = sorted(events, key=lambda e: e.start_datetime if e.start_datetime else "9999-99-99")
        
        # Caches for quick lookup
        project_cache = {}
        task_cache = {}

        def get_proj(pid):
            if not pid: return None
            if pid not in project_cache:
                project_cache[pid] = project_repo.get_by_id(pid)
            return project_cache[pid]

        def get_task(tid):
            if not tid: return None
            if tid not in task_cache:
                task_cache[tid] = task_repo.get_by_id(tid)
            return task_cache[tid]
            
        # Filter out events whose project or task is deleted or archived
        valid_events = []
        for ev in sorted_events:
            # Check project
            if ev.project_id:
                p = get_proj(ev.project_id)
                if p and (getattr(p, "is_archived", False) or getattr(p, "deleted_at", None) is not None):
                    continue
            # Check task
            if ev.task_id:
                t = get_task(ev.task_id)
                if t and (getattr(t, "is_archived", False) or getattr(t, "deleted_at", None) is not None):
                    continue
            valid_events.append(ev)

        def get_proj_name(pid):
            p = get_proj(pid)
            return p.name if p else f"Proj {pid}"

        def get_task_name(tid):
            t = get_task(tid)
            return t.title if t else f"Tarefa {tid}"

        from PySide6.QtGui import QColor
        theme_bg = QColor(BG_HOVER)

        if self.grouping == "project":
            # Group by Project, then sub-group by "Eventos de Projeto" and "Eventos de Tarefas"
            proj_groups = {}
            for ev in valid_events:
                if self.filter_task_id and ev.task_id != self.filter_task_id:
                    continue
                # filter
                if self.filter_project_id and ev.project_id != self.filter_project_id:
                    continue
                pid = ev.project_id or 0
                if pid not in proj_groups:
                    proj_groups[pid] = {"proj_events": [], "task_events": []}
                
                if ev.task_id:
                    proj_groups[pid]["task_events"].append(ev)
                else:
                    proj_groups[pid]["proj_events"].append(ev)

            for pid, groups in proj_groups.items():
                p_name = get_proj_name(pid) if pid != 0 else "Sem Projeto"
                total_ev = len(groups["proj_events"]) + len(groups["task_events"])
                
                proj_item = QTreeWidgetItem(self, [f"Proj. {p_name}", str(total_ev), "", "", ""])
                for col in range(5):
                    proj_item.setBackground(col, theme_bg)
                bold_font = QFont()
                bold_font.setBold(True)
                proj_item.setFont(0, bold_font)
                proj_item.setData(0, Qt.UserRole, None)
                
                if groups["proj_events"]:
                    sub_proj = QTreeWidgetItem(proj_item, ["Eventos de Projeto", str(len(groups["proj_events"])), "", "", ""])
                    sub_proj.setFont(0, bold_font)
                    sub_proj.setData(0, Qt.UserRole, None)
                    for ev in groups["proj_events"]:
                        self._add_event_item(sub_proj, ev, get_task_name)
                        
                if groups["task_events"]:
                    sub_task = QTreeWidgetItem(proj_item, ["Eventos de Tarefas", str(len(groups["task_events"])), "", "", ""])
                    sub_task.setFont(0, bold_font)
                    sub_task.setData(0, Qt.UserRole, None)
                    for ev in groups["task_events"]:
                        self._add_event_item(sub_task, ev, get_task_name)
                        
            self.expandAll()

        elif self.grouping == "date":
            # Group by Date directly
            date_groups = {}
            for ev in valid_events:
                if self.filter_task_id and ev.task_id != self.filter_task_id:
                    continue
                if self.filter_project_id and ev.project_id != self.filter_project_id:
                    continue
                d = ev.start_datetime.split("T")[0] if ev.start_datetime else "Sem Data"
                if d not in date_groups:
                    date_groups[d] = []
                date_groups[d].append(ev)
                
            for d, evs in date_groups.items():
                # Format date string nicely if possible
                display_date = d
                try:
                    from datetime import datetime
                    if d != "Sem Data":
                        dt = datetime.strptime(d, "%Y-%m-%d")
                        display_date = dt.strftime("%d/%m/%Y")
                except:
                    pass
                    
                date_item = QTreeWidgetItem(self, [display_date, str(len(evs)) + " eventos", "", "", ""])
                for col in range(5):
                    date_item.setBackground(col, theme_bg)
                bold_font = QFont()
                bold_font.setBold(True)
                date_item.setFont(0, bold_font)
                date_item.setData(0, Qt.UserRole, None)
                
                for ev in evs:
                    self._add_event_item(date_item, ev, get_task_name)
                    
            self.expandAll()

    def _add_event_item(self, parent_item, ev, get_task_name_func):
        date_str = ""
        if ev.start_datetime:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(ev.start_datetime)
                date_str = dt.strftime("%d/%m/%Y %H:%M")
            except:
                date_str = ev.start_datetime

        t_name = get_task_name_func(ev.task_id) if ev.task_id else ""
        
        tipo_evento = "Evento de Tarefa" if ev.task_id else "Evento de Projeto"
        
        item = QTreeWidgetItem(parent_item, [
            date_str,
            ev.title,
            "", # We use a QLabel for description to enable proper word-wrap
            t_name,
            tipo_evento
        ])
        
        desc_text = ev.description or ""
        if desc_text:
            from PySide6.QtWidgets import QLabel
            lbl = QLabel(desc_text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("background: transparent; padding: 2px;")
            self.setItemWidget(item, 2, lbl)
            
        # Data structure: { "id": ev.id, "task_id": ev.task_id, "project_id": ev.project_id }
        item.setData(0, Qt.UserRole, {
            "id": ev.id,
            "task_id": ev.task_id,
            "project_id": ev.project_id
        })
        
        # Dim if highlight mode
        if self.highlight_task_id and ev.task_id != self.highlight_task_id:
            dim_color = Qt.darkGray
            for col in range(4):
                item.setForeground(col, dim_color)

    def handle_double_click(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data.get("id"):
            self._open_edit(data["id"])

    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item: return
        data = item.data(0, Qt.UserRole)
        if not data or not data.get("id"): return
        
        event_id = data["id"]
        task_id = data.get("task_id")
        project_id = data.get("project_id")
        
        menu = QMenu(self)
        
        if task_id:
            if not self.highlight_task_id or self.highlight_task_id != task_id:
                open_task_action = QAction("📋 Abrir Tarefa", self)
                open_task_action.triggered.connect(lambda: self._open_task(task_id))
                menu.addAction(open_task_action)
        elif not task_id and project_id:
            open_proj_action = QAction("🗂️ Abrir Projeto", self)
            open_proj_action.triggered.connect(lambda: self._open_project(project_id))
            menu.addAction(open_proj_action)
            
        edit_action = QAction("✏️ Editar Evento", self)
        edit_action.triggered.connect(lambda: self._open_edit(event_id))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        del_action = QAction("🗑️ Excluir Evento", self)
        del_action.triggered.connect(lambda: self._delete_event(event_id))
        menu.addAction(del_action)
        
        menu.exec_(self.viewport().mapToGlobal(pos))
        
    def _open_edit(self, event_id):
        from gui.dialogs_qt.event_dialog_qt import EventDialogQt
        from services.event_service import EventService
        event_service = EventService()
        event = event_service.repo.get_by_id(event_id)
        if event:
            dialog = EventDialogQt(self, agenda_event=event)
            if dialog.exec():
                p = self.parent()
                while p:
                    if hasattr(p, "load_data"):
                        p.load_data()
                        break
                    p = p.parent()

    def _delete_event(self, event_id):
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar")
        msg.setText("Deseja mesmo excluir este evento?")
        btn_sim = msg.addButton("Sim", QMessageBox.YesRole)
        btn_nao = msg.addButton("Não", QMessageBox.NoRole)
        msg.exec()
        if msg.clickedButton() == btn_sim:
            from services.event_service import EventService
            EventService().delete(event_id)
            
            # Walk up to find load_data
            p = self.parent()
            while p:
                if hasattr(p, "load_data"):
                    p.load_data()
                    break
                p = p.parent()

    def _open_task(self, task_id):
        main_win = self.window()
        if main_win and hasattr(main_win, "show_task_detail"):
            main_win.show_task_detail(task_id, self.main_view)

    def _open_project(self, project_id):
        main_win = self.window()
        if main_win and hasattr(main_win, "show_project_360"):
            main_win.show_project_360(project_id, self.main_view)
