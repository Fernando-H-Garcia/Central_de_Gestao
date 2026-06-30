from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QMessageBox, QDateTimeEdit
)
from gui.theme import style_calendar_today

class EventDialogQt(QDialog):
    def __init__(self, parent=None, agenda_event=None, project_id=None, task_id=None):
        super().__init__(parent)
        
        self.agenda_event = agenda_event
        self.project_id = project_id
        self.task_id = task_id
        
        from services.event_service import EventService
        self.event_service = EventService()
        
        self.setWindowTitle("Editor de Evento")
        self.resize(500, 550)
        
        self.setup_ui()
        self.populate_fields()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        main_layout.addWidget(QLabel("Título do Evento:"))
        self.ent_title = QLineEdit()
        main_layout.addWidget(self.ent_title)
        
        from PySide6.QtWidgets import QHBoxLayout
        date_layout = QHBoxLayout()
        
        start_layout = QVBoxLayout()
        start_layout.addWidget(QLabel("Início:"))
        self.dt_start = QDateTimeEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDisplayFormat("dd/MM/yyyy HH:mm")
        style_calendar_today(self.dt_start)
        start_layout.addWidget(self.dt_start)
        date_layout.addLayout(start_layout)
        
        end_layout = QVBoxLayout()
        end_layout.addWidget(QLabel("Fim:"))
        self.dt_end = QDateTimeEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDisplayFormat("dd/MM/yyyy HH:mm")
        style_calendar_today(self.dt_end)
        end_layout.addWidget(self.dt_end)
        date_layout.addLayout(end_layout)
        
        main_layout.addLayout(date_layout)
        
        main_layout.addWidget(QLabel("Local/Link:"))
        self.ent_loc = QLineEdit()
        main_layout.addWidget(self.ent_loc)
        
        main_layout.addWidget(QLabel("Descrição / Alerta:"))
        self.ent_desc = QTextEdit()
        self.ent_desc.setMaximumHeight(100)
        main_layout.addWidget(self.ent_desc)
        
        main_layout.addStretch()
        
        self.btn_save = QPushButton("Salvar Evento")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save_event)
        main_layout.addWidget(self.btn_save)

    def populate_fields(self):
        from PySide6.QtCore import QDateTime
        import datetime
        if self.agenda_event:
            self.ent_title.setText(self.agenda_event.title)
            self.ent_loc.setText(self.agenda_event.location or "")
            self.ent_desc.setText(self.agenda_event.description or "")
            if self.agenda_event.start_datetime:
                try:
                    dt = datetime.datetime.fromisoformat(str(self.agenda_event.start_datetime))
                    self.dt_start.setDateTime(dt)
                except:
                    pass
            if self.agenda_event.end_datetime:
                try:
                    dt = datetime.datetime.fromisoformat(str(self.agenda_event.end_datetime))
                    self.dt_end.setDateTime(dt)
                except:
                    pass
        else:
            now = QDateTime.currentDateTime()
            self.dt_start.setDateTime(now)
            self.dt_end.setDateTime(now.addSecs(3600))

    def save_event(self):
        from models.entities import Event
        try:
            title = self.ent_title.text().strip()
            if not title:
                QMessageBox.warning(self, "Aviso", "O evento precisa de um título.")
                return
                
            start_dt = self.dt_start.dateTime().toPython().isoformat(sep=" ", timespec="minutes")
            end_dt = self.dt_end.dateTime().toPython().isoformat(sep=" ", timespec="minutes")
            loc = self.ent_loc.text().strip()
            desc = self.ent_desc.toPlainText().strip()
            
            if self.agenda_event:
                original = Event(title=self.agenda_event.title, description=self.agenda_event.description, start_datetime=self.agenda_event.start_datetime, end_datetime=self.agenda_event.end_datetime, location=self.agenda_event.location, notes=self.agenda_event.notes, project_id=self.agenda_event.project_id, task_id=self.agenda_event.task_id)
                self.agenda_event.title = title
                self.agenda_event.start_datetime = start_dt
                self.agenda_event.end_datetime = end_dt
                self.agenda_event.location = loc
                self.agenda_event.description = desc
                self.event_service.update(self.agenda_event, original)
            else:
                self.event_service.create(
                    title=title, description=desc, start=start_dt, end=end_dt, 
                    location=loc, project_id=self.project_id, task_id=self.task_id
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro no Python", str(e))
