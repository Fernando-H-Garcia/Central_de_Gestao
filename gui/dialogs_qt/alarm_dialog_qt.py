from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QDateEdit, QTimeEdit, QCheckBox, QScrollArea, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, QDate, QTime
from gui.theme import (
    set_combobox_colors, ENERGY_COLORS, apply_combobox_dynamic_color, get_energy_color
)
from services.alert_service import AlertService

# Mapeamento: exibição PT → valor BD
PRIORITY_MAP = {
    "Baixa":  "low",
    "Média":  "medium",
    "Alta":   "high",
    "Máxima": "critical",
}
PRIORITY_MAP_REVERSE = {v: k for k, v in PRIORITY_MAP.items()}


class AlarmDialogQt(QDialog):
    """Diálogo para criar ou editar um alarme."""

    def __init__(self, parent=None, task=None, alarm=None, on_save=None):
        super().__init__(parent)
        self.task = task
        self.alarm = alarm
        self.on_save = on_save
        self.alert_service = AlertService()

        if self.alarm:
            self.setWindowTitle("🔔 Editor de Alarme")
        else:
            title_str = f'para "{task.title}"' if task else ""
            self.setWindowTitle(f"🔔 Criar Alarme {title_str}")
            
        self.resize(480, 520)
        self.setup_ui()
        self.populate_data()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setObjectName("scroll_widget")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Tarefa vinculada (informativo)
        if self.task:
            lbl_task = QLabel(f"📋 Tarefa: <b>{self.task.title}</b>")
            lbl_task.setWordWrap(True)
            layout.addWidget(lbl_task)

        # Título
        layout.addWidget(QLabel("Título do Alarme:"))
        self.ent_title = QLineEdit()
        self.ent_title.setPlaceholderText("Ex: Verificar status do relatório")
        layout.addWidget(self.ent_title)

        # Descrição
        layout.addWidget(QLabel("Descrição (opcional):"))
        self.ent_desc = QTextEdit()
        self.ent_desc.setMaximumHeight(90)
        self.ent_desc.setPlaceholderText("Detalhes adicionais...")
        layout.addWidget(self.ent_desc)

        # Prioridade
        layout.addWidget(QLabel("Prioridade:"))
        self.opt_priority = QComboBox()
        self.opt_priority.addItems(list(PRIORITY_MAP.keys()))
        self.opt_priority.setCurrentText("Média")
        set_combobox_colors(self.opt_priority, ENERGY_COLORS)
        apply_combobox_dynamic_color(self.opt_priority, get_energy_color)
        layout.addWidget(self.opt_priority)

        # Data
        layout.addWidget(QLabel("Data do Alarme:"))
        self.ent_date = QDateEdit()
        self.ent_date.setCalendarPopup(True)
        self.ent_date.setDate(QDate.currentDate())
        self.ent_date.setDisplayFormat("dd/MM/yyyy")
        from gui.theme import style_calendar_today
        style_calendar_today(self.ent_date)
        layout.addWidget(self.ent_date)

        # Hora (opcional)
        row_time = QHBoxLayout()
        self.chk_time = QCheckBox("Hora específica:")
        self.chk_time.setChecked(False)
        self.ent_time = QTimeEdit()
        self.ent_time.setTime(QTime(9, 0))
        self.ent_time.setDisplayFormat("HH:mm")
        self.ent_time.setReadOnly(True)
        self.ent_time.setStyleSheet("""
            QTimeEdit {
                border-radius: 0px;
                background-color: #1c1c2e;
                color: #ffffff;
                border: 1px solid #2a2a3f;
                padding: 5px;
            }
            QTimeEdit:focus {
                border: 1px solid #4a6fe3;
            }
        """)
        self.chk_time.toggled.connect(lambda checked: self.ent_time.setReadOnly(not checked))
        row_time.addWidget(self.chk_time)
        row_time.addWidget(self.ent_time)
        row_time.addStretch()
        layout.addLayout(row_time)

        lbl_hint = QLabel(
            "💡 Sem hora definida: o alarme dispara durante todo o dia.\n"
            "   Com hora definida: só dispara a partir desse horário."
        )
        lbl_hint.setStyleSheet("color: #aaa; font-size: 11px;")
        lbl_hint.setWordWrap(True)
        layout.addWidget(lbl_hint)

        layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

        # Botões
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_text = "💾 Salvar" if self.alarm else "🔔 Criar Alarme"
        self.btn_save = QPushButton(btn_text)
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        main_layout.addLayout(btn_layout)

    def populate_data(self):
        if not self.alarm:
            return
            
        self.ent_title.setText(self.alarm.title or "")
        self.ent_desc.setText(self.alarm.description or "")
        
        priority_pt = PRIORITY_MAP_REVERSE.get(self.alarm.priority, "Média")
        self.opt_priority.setCurrentText(priority_pt)
        
        if self.alarm.alert_date:
            try:
                dt = QDate.fromString(self.alarm.alert_date, "yyyy-MM-dd")
                self.ent_date.setDate(dt)
            except Exception:
                pass
                
        if self.alarm.alert_time:
            self.chk_time.setChecked(True)
            self.ent_time.setReadOnly(False)
            try:
                t = QTime.fromString(self.alarm.alert_time, "HH:mm")
                self.ent_time.setTime(t)
            except Exception:
                pass
        else:
            self.chk_time.setChecked(False)
            self.ent_time.setTime(QTime(9, 0))

    def save(self):
        title = self.ent_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Aviso", "O título do alarme é obrigatório.")
            return

        description = self.ent_desc.toPlainText().strip() or None
        priority_pt = self.opt_priority.currentText()
        priority = PRIORITY_MAP.get(priority_pt, "medium")
        alert_date = self.ent_date.date().toString("yyyy-MM-dd")
        alert_time = None
        if self.chk_time.isChecked():
            alert_time = self.ent_time.time().toString("HH:mm")

        if self.alarm:
            import copy
            original = copy.deepcopy(self.alarm)
            self.alarm.title = title
            self.alarm.description = description
            self.alarm.priority = priority
            self.alarm.alert_date = alert_date
            self.alarm.alert_time = alert_time
            
            self.alert_service.update_alert(self.alarm, original)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated", {"entity_type": "alert", "entity_id": self.alarm.id})
            
            if self.on_save:
                self.on_save(self.alarm)
        else:
            entity_type = "task"
            entity_id = self.task.id if self.task else 0

            alarm = self.alert_service.create_alert(
                entity_type=entity_type,
                entity_id=entity_id,
                title=title,
                alert_date=alert_date,
                description=description,
                alert_time=alert_time,
                priority=priority,
                status="pending",
                recurrence_type="none",
            )
            
            from core.event_bus import event_bus
            event_bus.emit("entity_updated", {"entity_type": "alert", "entity_id": alarm.id})

            if self.on_save:
                self.on_save(alarm)

        self.accept()
