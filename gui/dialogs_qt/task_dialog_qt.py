from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QPushButton, QMessageBox, QDateEdit, QCheckBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QDate
from models.entities import Task
from services.project_service import ProjectService
import copy
from gui.theme import set_combobox_colors, STATUS_COLORS, ENERGY_COLORS, apply_combobox_dynamic_color, get_status_color, get_energy_color, style_calendar_today

class TaskDialogQt(QDialog):
    def __init__(self, parent=None, task: Task = None, on_save=None):
        super().__init__(parent)
        self.task = task
        self.on_save = on_save
        self.project_service = ProjectService()
        self.projects = self.project_service.get_all_active()
        
        self.setWindowTitle("Criação de Tarefa" if not task else "Editor de Tarefa")
        self.resize(500, 650)
        

        self.setup_ui()
        self.populate_fields()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setObjectName("scroll_widget")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        layout.addWidget(QLabel("Título:"))
        self.ent_title = QLineEdit()
        layout.addWidget(self.ent_title)
        
        # Context
        layout.addWidget(QLabel("Descrição / Contexto:"))
        self.ent_context = QTextEdit()
        self.ent_context.setMaximumHeight(100)
        layout.addWidget(self.ent_context)
        
        # Status
        layout.addWidget(QLabel("Status:"))
        self.opt_status = QComboBox()
        self.opt_status.addItems(["Pendente", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"])
        layout.addWidget(self.opt_status)
        
        # Energy
        layout.addWidget(QLabel("Prioridade / Energia:"))
        self.opt_energy = QComboBox()
        self.opt_energy.addItems(["Baixa", "Média", "Alta", "Máxima"])
        
        set_combobox_colors(self.opt_status, STATUS_COLORS)
        set_combobox_colors(self.opt_energy, ENERGY_COLORS)
        
        apply_combobox_dynamic_color(self.opt_status, get_status_color)
        apply_combobox_dynamic_color(self.opt_energy, get_energy_color)
        
        layout.addWidget(self.opt_energy)
        
        # Project
        layout.addWidget(QLabel("Projeto Vinculado:"))
        self.opt_proj = QComboBox()
        self.proj_dict = {"Nenhum": None}
        self.opt_proj.addItem("Nenhum")
        for p in self.projects:
            name = f"{p.id} - {p.name}"
            self.proj_dict[name] = p.id
            self.opt_proj.addItem(name)
        layout.addWidget(self.opt_proj)
        
        # Dates
        layout.addWidget(QLabel("Data Início:"))
        self.ent_start = QDateEdit()
        self.ent_start.setCalendarPopup(True)
        self.ent_start.setDate(QDate.currentDate())
        style_calendar_today(self.ent_start)
        layout.addWidget(self.ent_start)
        
        layout.addWidget(QLabel("Data Fim (Prazo):"))
        self.ent_due = QDateEdit()
        self.ent_due.setCalendarPopup(True)
        self.ent_due.setDate(QDate.currentDate())
        style_calendar_today(self.ent_due)
        layout.addWidget(self.ent_due)
        
        # Estimated Hours
        layout.addWidget(QLabel("Esforço Estimado (Horas):"))
        self.ent_estimated_hours = QLineEdit("0.0")
        layout.addWidget(self.ent_estimated_hours)
        
        # Milestone Checkbox
        self.chk_milestone = QCheckBox("É um Marco (Milestone - Sem duração/esforço)")
        layout.addWidget(self.chk_milestone)
        
        layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Save Button
        self.btn_save = QPushButton("Salvar Tarefa")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save)
        main_layout.addWidget(self.btn_save)
        
    def populate_fields(self):
        if self.task:
            self.ent_title.setText(self.task.title)
            if self.task.context:
                self.ent_context.setPlainText(self.task.context)
            self.opt_status.setCurrentText(self.task.status)
            self.opt_energy.setCurrentText(self.task.energy_level)
            
            if self.task.project_id:
                for k, v in self.proj_dict.items():
                    if v == self.task.project_id:
                        self.opt_proj.setCurrentText(k)
                        break
                        
            if self.task.start_date:
                start_date_str = str(self.task.start_date).split(' ')[0]
                qdate = QDate.fromString(start_date_str, "yyyy-MM-dd")
                if qdate.isValid():
                    self.ent_start.setDate(qdate)
                    
            if self.task.due_date:
                due_date_str = str(self.task.due_date).split(' ')[0]
                qdate = QDate.fromString(due_date_str, "yyyy-MM-dd")
                if qdate.isValid():
                    self.ent_due.setDate(qdate)
            self.ent_estimated_hours.setText(str(getattr(self.task, "estimated_hours", 0.0)))
            self.chk_milestone.setChecked(getattr(self.task, "is_milestone", False))
        else:
            self.opt_status.setCurrentText("Pendente")
            self.opt_energy.setCurrentText("Média")
            
    def save(self):
        title = self.ent_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Aviso", "O título da tarefa é obrigatório.")
            return
            
        context = self.ent_context.toPlainText().strip()
        status = self.opt_status.currentText()
        energy = self.opt_energy.currentText()
        
        proj_sel = self.opt_proj.currentText()
        proj_id = self.proj_dict.get(proj_sel)
        
        start_date = self.ent_start.date().toString("yyyy-MM-dd")
        due_date = self.ent_due.date().toString("yyyy-MM-dd")
        
        try:
            est_hours = float(self.ent_estimated_hours.text().strip() or 0.0)
        except ValueError:
            est_hours = 0.0
            
        is_ms = self.chk_milestone.isChecked()
        
        if self.task:
            import copy
            original_task = copy.deepcopy(self.task)
            self.task.title = title
            self.task.context = context
            self.task.status = status
            self.task.energy_level = energy
            self.task.project_id = proj_id
            self.task.start_date = start_date
            self.task.due_date = due_date
            self.task.estimated_hours = est_hours
            self.task.is_milestone = is_ms
            if self.on_save:
                self.on_save(self.task, False, original_task)
        else:
            new_task = Task(
                title=title, context=context, status=status, 
                energy_level=energy, project_id=proj_id, 
                start_date=start_date, due_date=due_date, estimated_hours=est_hours, 
                is_milestone=is_ms
            )
            if self.on_save:
                self.on_save(new_task, True, None)
                
        self.accept()
