from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu, QMessageBox
)
from PySide6.QtGui import QAction, QColor, QBrush, QFont
from PySide6.QtCore import Qt
from gui.theme import GLOBAL_STYLE, BG_HOVER, get_energy_color

class AlarmTreeWidget(QTreeWidget):
    def __init__(self, grouping="project", filter_project_id=None, highlight_task_id=None, main_window=None, parent=None):
        super().__init__(parent)
        self.grouping = grouping # "project" or "date"
        self.filter_project_id = filter_project_id
        self.highlight_task_id = highlight_task_id
        self.main_window = main_window
        self.main_view = parent
        
        self.setColumnCount(5)
        self.setHeaderLabels(["Data / Hora", "Prioridade", "Título", "Descrição", "Tarefa"])
        self.setWordWrap(True)
        
        # Adjust column widths
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.setColumnWidth(2, 200)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        self.setTextElideMode(Qt.ElideNone)
        
        self.setAlternatingRowColors(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setIndentation(20)
        
        # Double click to open edit
        self.itemDoubleClicked.connect(self.handle_double_click)

    def populate(self, alarms, project_repo, task_repo):
        self.clear()
        
        # Sort alarms by date
        sorted_alarms = sorted(alarms, key=lambda a: a.alert_date if a.alert_date else "9999-99-99")
        
        # Caches for quick lookup
        project_cache = {}
        task_cache = {}

        def get_task(tid):
            if not tid: return None
            if tid not in task_cache:
                task_cache[tid] = task_repo.get_by_id(tid)
            return task_cache[tid]

        def get_proj(pid):
            if not pid: return None
            if pid not in project_cache:
                project_cache[pid] = project_repo.get_by_id(pid)
            return project_cache[pid]
            
        # Filter valid alarms
        valid_alarms = []
        for al in sorted_alarms:
            t = get_task(al.entity_id) if al.entity_type == "task" else None
            if t:
                # Check task
                if getattr(t, "is_archived", False) or getattr(t, "deleted_at", None) is not None:
                    continue
                # Check project
                if t.project_id:
                    p = get_proj(t.project_id)
                    if p and (getattr(p, "is_archived", False) or getattr(p, "deleted_at", None) is not None):
                        continue
            elif al.entity_type == "project":
                p = get_proj(al.entity_id)
                if p and (getattr(p, "is_archived", False) or getattr(p, "deleted_at", None) is not None):
                    continue
            valid_alarms.append(al)

        def get_proj_name(pid):
            p = get_proj(pid)
            return p.name if p else f"Proj {pid}"

        def get_task_name(tid):
            t = get_task(tid)
            return t.title if t else f"Tarefa {tid}"

        theme_bg = QColor(BG_HOVER)

        if self.grouping == "project":
            proj_groups = {}
            for al in valid_alarms:
                pid = 0
                if al.entity_type == "task":
                    t = get_task(al.entity_id)
                    pid = t.project_id if t and t.project_id else 0
                elif al.entity_type == "project":
                    pid = al.entity_id
                
                if self.filter_project_id and pid != self.filter_project_id:
                    continue
                
                if pid not in proj_groups:
                    proj_groups[pid] = []
                
                proj_groups[pid].append(al)

            for pid, groups in proj_groups.items():
                p_name = get_proj_name(pid) if pid != 0 else "Sem Projeto"
                total_al = len(groups)
                
                proj_item = QTreeWidgetItem(self, [f"Proj. {p_name}", "", "", "", str(total_al)])
                for col in range(5):
                    proj_item.setBackground(col, theme_bg)
                bold_font = QFont()
                bold_font.setBold(True)
                proj_item.setFont(0, bold_font)
                proj_item.setData(0, Qt.UserRole, None)
                
                for al in groups:
                    self._add_alarm_item(proj_item, al, get_task_name)
                        
            self.expandAll()

        elif self.grouping == "date":
            date_groups = {}
            for al in valid_alarms:
                pid = 0
                if al.entity_type == "task":
                    t = get_task(al.entity_id)
                    pid = t.project_id if t and t.project_id else 0
                elif al.entity_type == "project":
                    pid = al.entity_id

                if self.filter_project_id and pid != self.filter_project_id:
                    continue
                
                d = al.alert_date if al.alert_date else "Sem Data"
                if d not in date_groups:
                    date_groups[d] = []
                date_groups[d].append(al)
                
            for d, als in date_groups.items():
                display_date = d
                try:
                    from datetime import datetime
                    if d != "Sem Data":
                        dt = datetime.strptime(d, "%Y-%m-%d")
                        display_date = dt.strftime("%d/%m/%Y")
                except:
                    pass
                    
                date_item = QTreeWidgetItem(self, [display_date, "", "", "", str(len(als)) + " alarmes"])
                for col in range(5):
                    date_item.setBackground(col, theme_bg)
                bold_font = QFont()
                bold_font.setBold(True)
                date_item.setFont(0, bold_font)
                date_item.setData(0, Qt.UserRole, None)
                
                for al in als:
                    self._add_alarm_item(date_item, al, get_task_name)
                    
            self.expandAll()

    def _add_alarm_item(self, parent_item, al, get_task_name_func):
        date_str = ""
        if al.alert_date:
            try:
                from datetime import datetime
                dt = datetime.strptime(al.alert_date, "%Y-%m-%d")
                date_str = dt.strftime("%d/%m/%Y")
                if al.alert_time:
                    date_str += f" {al.alert_time}"
            except:
                date_str = al.alert_date

        t_name = get_task_name_func(al.entity_id) if al.entity_type == "task" else ""
        
        priority_labels = {
            "low": "Baixa",
            "medium": "Média",
            "high": "Alta",
            "critical": "Máxima"
        }
        prio_pt = priority_labels.get(al.priority, "Média")
        
        item = QTreeWidgetItem(parent_item, [
            date_str,
            prio_pt,
            al.title,
            "",
            t_name
        ])
        
        color = get_energy_color(prio_pt)
        item.setForeground(1, QBrush(QColor(color)))
        
        desc_text = al.description or ""
        if desc_text:
            from PySide6.QtWidgets import QLabel
            lbl = QLabel(desc_text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("background: transparent; padding: 2px;")
            self.setItemWidget(item, 3, lbl)
            
        item.setData(0, Qt.UserRole, {
            "id": al.id,
            "entity_id": al.entity_id,
            "entity_type": al.entity_type
        })
        
        if self.highlight_task_id and al.entity_type == "task" and al.entity_id != self.highlight_task_id:
            dim_color = Qt.darkGray
            for col in range(5):
                item.setForeground(col, dim_color)
            if desc_text:
                lbl.setStyleSheet("background: transparent; padding: 2px; color: #555555;")

    def handle_double_click(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data and data.get("id"):
            self._open_edit(data["id"])

    def show_context_menu(self, pos):
        item = self.itemAt(pos)
        if not item: return
        data = item.data(0, Qt.UserRole)
        if not data or not data.get("id"): return
        
        alarm_id = data["id"]
        entity_id = data.get("entity_id")
        entity_type = data.get("entity_type")
        
        menu = QMenu(self)
        
        if entity_type == "task":
            if not self.highlight_task_id or self.highlight_task_id != entity_id:
                open_task_action = QAction("📋 Abrir Tarefa", self)
                open_task_action.triggered.connect(lambda: self._open_task(entity_id))
                menu.addAction(open_task_action)
        elif entity_type == "project":
            open_proj_action = QAction("🗂️ Abrir Projeto", self)
            open_proj_action.triggered.connect(lambda: self._open_project(entity_id))
            menu.addAction(open_proj_action)
            
        edit_action = QAction("✏️ Editar", self)
        edit_action.triggered.connect(lambda: self._open_edit(alarm_id))
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        del_action = QAction("🗑️ Excluir", self)
        del_action.triggered.connect(lambda: self._delete_alarm(alarm_id))
        menu.addAction(del_action)
        
        menu.exec_(self.viewport().mapToGlobal(pos))
        
    def _open_edit(self, alarm_id):
        from gui.dialogs_qt.alarm_dialog_qt import AlarmDialogQt
        from services.alert_service import AlertService
        alert_service = AlertService()
        alarm = alert_service.get_alert(alarm_id)
        if alarm:
            dialog = AlarmDialogQt(self, alarm=alarm)
            if dialog.exec():
                p = self.parent()
                while p:
                    if hasattr(p, "load_data"):
                        p.load_data()
                        break
                    p = p.parent()

    def _delete_alarm(self, alarm_id):
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar")
        msg.setText("Deseja mesmo excluir este alarme?")
        btn_sim = msg.addButton("Sim", QMessageBox.YesRole)
        btn_nao = msg.addButton("Não", QMessageBox.NoRole)
        msg.exec()
        if msg.clickedButton() == btn_sim:
            from services.alert_service import AlertService
            AlertService().delete_alert(alarm_id)
            
            p = self.parent()
            while p:
                if hasattr(p, "load_data"):
                    p.load_data()
                    break
                p = p.parent()
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")

    def _open_task(self, task_id):
        main_win = self.window()
        if main_win and hasattr(main_win, "show_task_detail"):
            main_win.show_task_detail(task_id, self.main_view)

    def _open_project(self, project_id):
        main_win = self.window()
        if main_win and hasattr(main_win, "show_project_360"):
            main_win.show_project_360(project_id, self.main_view)
