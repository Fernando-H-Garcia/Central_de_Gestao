from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QDateEdit, QTimeEdit, QCheckBox, QSpinBox, QScrollArea, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, QDate, QTime
from gui.theme import (
    set_combobox_colors, ENERGY_COLORS, apply_combobox_dynamic_color, get_energy_color,
    CHECKBOX_STYLE
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

    def __init__(self, parent=None, task=None, alarm=None, on_save=None, initial_dt=None):
        super().__init__(parent)
        self.task = task
        self.alarm = alarm
        self.on_save = on_save
        self.initial_dt = initial_dt
        self.alert_service = AlertService()

        if self.alarm:
            self.setWindowTitle("🔔 Editor de Alarme")
        else:
            title_str = f'para "{task.title}"' if task else ""
            self.setWindowTitle(f"🔔 Criar Alarme {title_str}")
            
        self.resize(480, 600)
        self.setup_ui()
        self.populate_data()
        # pré-preenche com data sob o mouse (planejamento) quando criando
        if not self.alarm and self.initial_dt is not None:
            try:
                import datetime as _dt
                dt = self.initial_dt
                # aceita date ou datetime
                if isinstance(dt, _dt.date) and not isinstance(dt, _dt.datetime):
                    dt = _dt.datetime.combine(dt, _dt.time(9, 0))
                self.ent_date.setDate(QDate(dt.year, dt.month, dt.day))
                # se tiver hora não-meia-noite, preenche hora e ativa
                if dt.hour != 0 or dt.minute != 0:
                    self.chk_time.setChecked(True)
                    self.ent_time.setReadOnly(False)
                    self.ent_time.setTime(QTime(dt.hour, dt.minute))
            except Exception:
                pass
        # ajusta altura ao conteúdo (sem obrigar scroll para o Repetir)
        self.adjustSize()
        if self.height() < 600:
            self.resize(480, 600)

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
        self.chk_time.setStyleSheet(CHECKBOX_STYLE)
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

        # Repetir alarme a cada X dias Y vezes
        repeat_row = QHBoxLayout()
        self.chk_repeat = QCheckBox("🔁 Repetir a cada")
        self.chk_repeat.setStyleSheet(CHECKBOX_STYLE)
        self.chk_repeat.setChecked(False)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 365)
        self.spin_interval.setValue(1)
        self.spin_interval.setSuffix(" dias")
        self.spin_interval.setFixedWidth(95)
        self.spin_interval.setEnabled(False)
        self.spin_count = QSpinBox()
        self.spin_count.setRange(2, 100)
        self.spin_count.setValue(3)
        self.spin_count.setSuffix(" vezes")
        self.spin_count.setFixedWidth(95)
        self.spin_count.setEnabled(False)
        self.chk_repeat.toggled.connect(lambda c: (self.spin_interval.setEnabled(c), self.spin_count.setEnabled(c)))
        repeat_row.addWidget(self.chk_repeat)
        repeat_row.addWidget(self.spin_interval)
        lbl_vezes = QLabel("×")
        lbl_vezes.setStyleSheet("color: #aaa;")
        repeat_row.addWidget(lbl_vezes)
        repeat_row.addWidget(self.spin_count)
        repeat_row.addStretch()
        layout.addLayout(repeat_row)
        self.lbl_repeat_hint = QLabel("Serão criados Y alarmes a cada X dias a partir da data acima.")
        self.lbl_repeat_hint.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_repeat_hint.setVisible(False)
        self.chk_repeat.toggled.connect(self.lbl_repeat_hint.setVisible)
        layout.addWidget(self.lbl_repeat_hint)

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

        # repetir
        ri = getattr(self.alarm, 'recurrence_interval', None)
        rc = getattr(self.alarm, 'recurrence_count', None)
        if ri and rc and int(rc) > 1:
            self.chk_repeat.setChecked(True)
            self.spin_interval.setValue(int(ri))
            self.spin_count.setValue(int(rc))
            self.spin_interval.setEnabled(True)
            self.spin_count.setEnabled(True)
            self.lbl_repeat_hint.setVisible(True)

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
        do_repeat = self.chk_repeat.isChecked()
        interval = self.spin_interval.value() if do_repeat else None
        count = self.spin_count.value() if do_repeat else None
        if do_repeat and (not interval or not count or count < 2):
            QMessageBox.warning(self, "Aviso", "Defina intervalo e quantidade válidos para repetição (Y ≥ 2).")
            return

        if self.alarm:
            import copy
            original = copy.deepcopy(self.alarm)
            self.alarm.title = title
            self.alarm.description = description
            self.alarm.priority = priority
            self.alarm.alert_date = alert_date
            self.alarm.alert_time = alert_time
            # repetição
            if do_repeat:
                # se já fazia parte de série, mantém grupo; senão cria novo
                import uuid as _uuid
                grp = getattr(self.alarm, 'recurrence_group_id', None) or str(_uuid.uuid4())
                self.alarm.recurrence_type = "custom"
                self.alarm.recurrence_interval = interval
                self.alarm.recurrence_count = count
                self.alarm.recurrence_group_id = grp
            else:
                self.alarm.recurrence_type = "none"
                self.alarm.recurrence_interval = None
                self.alarm.recurrence_count = None
                self.alarm.recurrence_group_id = None
            
            self.alert_service.update_alert(self.alarm, original)
            from core.event_bus import event_bus
            event_bus.emit("entity_updated", {"entity_type": "alert", "entity_id": self.alarm.id})

            # se ativou repetição agora e era alarme único, cria os Y-1 restantes
            if do_repeat and getattr(original, 'recurrence_group_id', None) is None:
                from datetime import datetime as _dt, timedelta
                base = _dt.strptime(alert_date, "%Y-%m-%d")
                grp = self.alarm.recurrence_group_id
                for i in range(1, count):
                    d = (base + timedelta(days=interval * i)).strftime("%Y-%m-%d")
                    t = f"{title} ({i+1}/{count})" if count > 1 else title
                    self.alert_service.create_alert(
                        entity_type=self.alarm.entity_type,
                        entity_id=self.alarm.entity_id,
                        title=t,
                        alert_date=d,
                        description=description,
                        alert_time=alert_time,
                        priority=priority,
                        status="pending",
                        recurrence_type="custom",
                        recurrence_interval=interval,
                        recurrence_count=count,
                        recurrence_group_id=grp
                    )
                event_bus.emit("entity_updated", {"entity_type": "alert", "entity_id": self.alarm.id})
            
            if self.on_save:
                self.on_save(self.alarm)
        else:
            entity_type = "task"
            entity_id = self.task.id if self.task else 0

            if do_repeat:
                alarms = self.alert_service.create_repeated_alerts(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    title=title,
                    alert_date=alert_date,
                    description=description,
                    alert_time=alert_time,
                    priority=priority,
                    recurrence_interval=interval,
                    recurrence_count=count
                )
                from core.event_bus import event_bus
                event_bus.emit("entity_updated", {"entity_type": "alert", "entity_id": alarms[0].id if alarms else 0})
                if self.on_save:
                    self.on_save(alarms[0] if alarms else None)
            else:
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
