from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from gui.theme import (
    BG_CARD, BG_HOVER, BG_SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_BODY, TEXT_DISABLED,
    ACCENT_BLUE, SUCCESS_GREEN, WARNING_ORANGE, ERROR_RED,
    BORDER_SUBTLE, RADIUS_MD, RADIUS_SM,
    FONT_CAPTION, FONT_BODY, FONT_BODY_LG, FONT_SUBTITLE,
)
from services.alert_service import AlertService
from services.task_service import TaskService
from services.project_service import ProjectService

PRIORITY_LABELS = {
    "low": "Baixa",
    "medium": "Média",
    "high": "Alta",
    "critical": "Máxima",
}

PRIORITY_COLORS = {
    "low": ACCENT_BLUE,
    "medium": SUCCESS_GREEN,
    "high": WARNING_ORANGE,
    "critical": ERROR_RED,
}

PRIORITY_EMOJIS = {
    "low": "🔵",
    "medium": "🟡",
    "high": "🟠",
    "critical": "🔴",
}

class AlarmCard(QFrame):
    def __init__(self, alarm, task_name, project_name, on_edit, on_delete, parent=None):
        super().__init__(parent)
        self.alarm = alarm
        self.task_name = task_name
        self.project_name = project_name
        self.on_edit = on_edit
        self.on_delete = on_delete
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("alarm_card")
        self.setStyleSheet(f"""
            QFrame#alarm_card {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER_SUBTLE};
                border-radius: {RADIUS_MD}px;
                margin: 2px 0px;
            }}
            QFrame#alarm_card:hover {{
                border: 1px solid {ACCENT_BLUE};
            }}
        """)
        self._build()

    def apply_dimmed(self):
        self.setStyleSheet(f"""
            QFrame#alarm_card {{
                background-color: {BG_CARD};
                border: 1px solid #252540;
                border-radius: {RADIUS_MD}px;
                margin: 2px 0px;
            }}
            QFrame#alarm_card:hover {{
                border: 1px solid #3a3a5f;
            }}
        """)
        for child in self.findChildren(QLabel):
            cs = child.styleSheet()
            child.setStyleSheet(cs + f" color: {TEXT_DISABLED};")

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Top row: priority badge + title
        top = QHBoxLayout()
        top.setSpacing(8)
        
        label_pt = PRIORITY_LABELS.get(self.alarm.priority, "Média")
        color = PRIORITY_COLORS.get(self.alarm.priority, SUCCESS_GREEN)
        emoji = PRIORITY_EMOJIS.get(self.alarm.priority, "🟡")
        
        badge = QLabel(f"{emoji} {label_pt}")
        badge.setStyleSheet(f"""
            background-color: {color};
            color: white;
            border-radius: {RADIUS_SM}px;
            padding: 2px 8px;
            font-size: {FONT_CAPTION}px;
            font-weight: bold;
        """)
        badge.setFixedHeight(22)
        top.addWidget(badge)
        top.addStretch()

        lbl_title = QLabel(self.alarm.title)
        font = QFont()
        font.setPointSize(FONT_BODY_LG)
        font.setBold(True)
        lbl_title.setFont(font)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        top.addWidget(lbl_title, stretch=1)
        layout.addLayout(top)

        # Description
        if self.alarm.description:
            lbl_desc = QLabel(self.alarm.description)
            lbl_desc.setWordWrap(True)
            lbl_desc.setStyleSheet(f"color: {TEXT_BODY}; font-size: {FONT_BODY}px;")
            layout.addWidget(lbl_desc)

        # Meta info: project + task + time
        meta = QHBoxLayout()
        meta.setSpacing(12)
        
        if self.project_name:
            lbl_proj = QLabel(f"📁 {self.project_name}")
            lbl_proj.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_CAPTION}px;")
            meta.addWidget(lbl_proj)
        
        if self.task_name:
            lbl_task = QLabel(f"📋 {self.task_name}")
            lbl_task.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_CAPTION}px;")
            meta.addWidget(lbl_task)
        
        meta.addStretch()
        
        # Date/time
        date_display = self.alarm.alert_date
        try:
            from datetime import datetime
            dt = datetime.strptime(self.alarm.alert_date, "%Y-%m-%d")
            date_display = dt.strftime("%d/%m/%Y")
        except Exception:
            pass
        hora = f" às {self.alarm.alert_time}" if self.alarm.alert_time else ""
        lbl_date = QLabel(f"🗓 {date_display}{hora}")
        lbl_date.setStyleSheet(f"color: {ACCENT_BLUE}; font-size: {FONT_CAPTION}px; font-weight: bold;")
        meta.addWidget(lbl_date)
        
        layout.addLayout(meta)

        # Action buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        
        btn_edit = QPushButton("✏️ Editar")
        btn_edit.setObjectName("secondary")
        btn_edit.setMinimumHeight(32)
        btn_edit.setStyleSheet(f"""
            QPushButton#secondary {{
                background-color: transparent;
                border: 1px solid {BORDER_SUBTLE};
                color: {TEXT_SECONDARY};
                padding: 6px 14px;
                border-radius: {RADIUS_SM}px;
                font-weight: bold;
                font-size: {FONT_CAPTION}px;
            }}
            QPushButton#secondary:hover {{
                background-color: {BG_HOVER};
                color: {TEXT_PRIMARY};
                border: 1px solid {ACCENT_BLUE};
            }}
            QPushButton#secondary:pressed {{
                background-color: {BORDER_SUBTLE};
            }}
        """)
        btn_edit.clicked.connect(lambda: self.on_edit(self.alarm.id))
        btn_row.addWidget(btn_edit)

        btn_delete = QPushButton("🗑️ Excluir")
        btn_delete.setObjectName("danger")
        btn_delete.setMinimumHeight(32)
        btn_delete.setStyleSheet(f"""
            QPushButton#danger {{
                background-color: transparent;
                border: 1px solid {ERROR_RED};
                color: {ERROR_RED};
                padding: 6px 14px;
                border-radius: {RADIUS_SM}px;
                font-weight: bold;
                font-size: {FONT_CAPTION}px;
            }}
            QPushButton#danger:hover {{
                background-color: {ERROR_RED};
                color: white;
            }}
            QPushButton#danger:pressed {{
                background-color: #b02a27;
            }}
        """)
        btn_delete.clicked.connect(lambda: self.on_delete(self.alarm.id))
        btn_row.addWidget(btn_delete)
        
        layout.addLayout(btn_row)


class DateGroupHeader(QFrame):
    def __init__(self, label, count, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            background-color: {BG_SECONDARY};
            border-radius: {RADIUS_MD}px;
            padding: 8px 12px;
            margin: 8px 0px 4px 0px;
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        
        lbl = QLabel(f"📅 {label}")
        font = QFont()
        font.setPointSize(FONT_SUBTITLE)
        font.setBold(True)
        lbl.setFont(font)
        lbl.setStyleSheet(f"color: {ACCENT_BLUE};")
        layout.addWidget(lbl)
        
        layout.addStretch()
        
        lbl_count = QLabel(f"{count} alarme{'s' if count != 1 else ''}")
        lbl_count.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_CAPTION}px;")
        layout.addWidget(lbl_count)


class AlarmCardsWidget(QWidget):
    def __init__(self, grouping="date", filter_project_id=None, highlight_task_id=None, main_window=None, parent=None):
        super().__init__(parent)
        self.grouping = grouping
        self.filter_project_id = filter_project_id
        self.highlight_task_id = highlight_task_id
        self.main_window = main_window
        
        self.task_service = TaskService()
        self.project_service = ProjectService()
        self.alert_service = AlertService()
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.container)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(0)
        self.cards_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll)

    def populate(self, alarms):
        # Clear existing cards
        while self.cards_layout.count() > 1:  # Keep the stretch
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Sort alarms by date
        sorted_alarms = sorted(alarms, key=lambda a: a.alert_date if a.alert_date else "9999-99-99")

        # Filter valid alarms
        valid_alarms = []
        for al in sorted_alarms:
            task = self.task_service.task_repo.get_by_id(al.entity_id) if al.entity_type == "task" else None
            if task:
                if getattr(task, "is_archived", False) or getattr(task, "deleted_at", None) is not None:
                    continue
                if task.project_id:
                    proj = self.project_service.project_repo.get_by_id(task.project_id)
                    if proj and (getattr(proj, "is_archived", False) or getattr(proj, "deleted_at", None) is not None):
                        continue
            elif al.entity_type == "project":
                proj = self.project_service.project_repo.get_by_id(al.entity_id)
                if proj and (getattr(proj, "is_archived", False) or getattr(proj, "deleted_at", None) is not None):
                    continue
            valid_alarms.append(al)

        if self.grouping == "project":
            self._populate_by_project(valid_alarms)
        else:
            self._populate_by_date(valid_alarms)

    def _populate_by_project(self, alarms):
        proj_groups = {}
        for al in alarms:
            pid = 0
            if al.entity_type == "task":
                task = self.task_service.task_repo.get_by_id(al.entity_id)
                pid = task.project_id if task and task.project_id else 0
            elif al.entity_type == "project":
                pid = al.entity_id

            if self.filter_project_id and pid != self.filter_project_id:
                continue

            if pid not in proj_groups:
                proj_groups[pid] = []
            proj_groups[pid].append(al)

        for pid, groups in proj_groups.items():
            proj = self.project_service.project_repo.get_by_id(pid) if pid != 0 else None
            p_name = proj.name if proj else "Sem Projeto"
            
            header = DateGroupHeader(p_name, len(groups))
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, header)

            for al in groups:
                self._add_alarm_card(al)

    def _populate_by_date(self, alarms):
        from datetime import datetime, date
        
        today = date.today()
        tomorrow = date.fromordinal(today.toordinal() + 1)
        
        date_groups = {}
        for al in alarms:
            pid = 0
            if al.entity_type == "task":
                task = self.task_service.task_repo.get_by_id(al.entity_id)
                pid = task.project_id if task and task.project_id else 0
            elif al.entity_type == "project":
                pid = al.entity_id

            if self.filter_project_id and pid != self.filter_project_id:
                continue

            d = al.alert_date if al.alert_date else "Sem Data"
            if d not in date_groups:
                date_groups[d] = []
            date_groups[d].append(al)

        # Sort dates: overdue first, then today, tomorrow, then future
        def sort_key(d):
            if d == "Sem Data":
                return (9999, "")
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").date()
                if dt < today:
                    return (0, d)  # overdue
                elif dt == today:
                    return (1, d)  # today
                elif dt == tomorrow:
                    return (2, d)  # tomorrow
                else:
                    return (3, d)  # future
            except:
                return (9999, d)

        for d in sorted(date_groups.keys(), key=sort_key):
            als = date_groups[d]
            
            # Determine label
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").date()
                if dt < today:
                    label = "ATRASADOS"
                elif dt == today:
                    label = "HOJE"
                elif dt == tomorrow:
                    label = "AMANHÃ"
                else:
                    label = dt.strftime("%d/%m/%Y")
            except:
                label = d

            header = DateGroupHeader(label, len(als))
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, header)

            for al in als:
                self._add_alarm_card(al)

    def _add_alarm_card(self, al):
        task_name = ""
        project_name = ""
        entity_id = al.entity_id
        entity_type = al.entity_type

        if entity_type == "task":
            task = self.task_service.task_repo.get_by_id(entity_id)
            if task:
                task_name = task.title
                if task.project_id:
                    proj = self.project_service.project_repo.get_by_id(task.project_id)
                    if proj:
                        project_name = proj.name
        elif entity_type == "project":
            proj = self.project_service.project_repo.get_by_id(entity_id)
            if proj:
                project_name = proj.name

        card = AlarmCard(
            alarm=al,
            task_name=task_name,
            project_name=project_name,
            on_edit=self._open_edit,
            on_delete=self._delete_alarm,
            parent=self.container
        )

        # Dim cards not matching highlight_task_id
        if self.highlight_task_id and entity_type == "task" and entity_id != self.highlight_task_id:
            card.apply_dimmed()

        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _open_edit(self, alarm_id):
        from gui.dialogs_qt.alarm_dialog_qt import AlarmDialogQt
        alarm = self.alert_service.get_alert(alarm_id)
        if alarm:
            dialog = AlarmDialogQt(self, alarm=alarm)
            if dialog.exec():
                self._reload_parent()

    def _delete_alarm(self, alarm_id):
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar")
        msg.setText("Deseja mesmo excluir este alarme?")
        btn_sim = msg.addButton("Sim", QMessageBox.YesRole)
        btn_nao = msg.addButton("Não", QMessageBox.NoRole)
        msg.exec()
        if msg.clickedButton() == btn_sim:
            self.alert_service.delete_alert(alarm_id)
            self._reload_parent()
            from core.event_bus import event_bus
            event_bus.emit("entity_updated")

    def _open_entity(self, alarm_id):
        alarm = self.alert_service.get_alert(alarm_id)
        if not alarm:
            return
        if alarm.entity_type == "task":
            if self.main_window and hasattr(self.main_window, "show_task_detail"):
                self.main_window.show_task_detail(alarm.entity_id, self)
        elif alarm.entity_type == "project":
            if self.main_window and hasattr(self.main_window, "show_project_360"):
                self.main_window.show_project_360(alarm.entity_id, self)

    def _reload_parent(self):
        p = self.parent()
        while p:
            if hasattr(p, "load_data"):
                p.load_data()
                break
            p = p.parent()

    def load_data(self, alarms):
        self.populate(alarms)