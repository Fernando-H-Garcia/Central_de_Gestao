from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QMessageBox, QDateEdit, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QDate
from services.agenda_service import AgendaService
from services.task_service import TaskService
from services.project_service import ProjectService
from core.event_bus import event_bus
from gui.theme import style_calendar_today

class ScheduleDialogQt(QDialog):
    def __init__(self, parent=None, entity_type="", entity_id=0, agenda_item=None, on_save=None):
        super().__init__(parent)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.agenda_item = agenda_item
        self.on_save = on_save
        
        self.agenda_service = AgendaService()
        self.task_service = TaskService()
        self.project_service = ProjectService()
        
        self.setWindowTitle("Programar Período de Trabalho" if not agenda_item else "Editar Período")
        self.resize(480, 550)
        
        self.setup_ui()
        self.populate_fields()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Load entity title
        title_text = f"{self.entity_type.capitalize()} ID: {self.entity_id}"
        self.default_effort = "0.0"
        if self.entity_type == 'task':
            t = self.task_service.task_repo.get_by_id(self.entity_id)
            if t:
                title_text = f"Tarefa: {t.title}"
                self.default_effort = str(getattr(t, "estimated_hours", 0.0))
        elif self.entity_type == 'project':
            p = self.project_service.project_repo.get_by_id(self.entity_id)
            if p:
                title_text = f"Projeto: {p.name}"

        lbl_header = QLabel(title_text)
        lbl_header.setObjectName("header")
        lbl_header.setWordWrap(True)
        main_layout.addWidget(lbl_header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_widget.setObjectName("scroll_widget")
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(20, 10, 20, 20)
        
        layout.addWidget(QLabel("Data Inicial:"))
        self.dp_start = QDateEdit()
        self.dp_start.setCalendarPopup(True)
        self.dp_start.setDate(QDate.currentDate())
        style_calendar_today(self.dp_start)
        layout.addWidget(self.dp_start)
        
        layout.addWidget(QLabel("Data Final:"))
        self.dp_end = QDateEdit()
        self.dp_end.setCalendarPopup(True)
        self.dp_end.setDate(QDate.currentDate())
        style_calendar_today(self.dp_end)
        layout.addWidget(self.dp_end)
        
        layout.addWidget(QLabel("Esforço Estimado (Horas):"))
        self.ent_effort = QLineEdit(self.default_effort)
        layout.addWidget(self.ent_effort)
        
        layout.addWidget(QLabel("Status do Agendamento:"))
        self.opt_status = QComboBox()
        self.opt_status.addItems(["planejado", "em_andamento", "pausado", "concluido"])
        layout.addWidget(self.opt_status)
        
        if self.entity_type == 'task':
            layout.addWidget(QLabel("Dependência (Requer que a tarefa abaixo termine):"))
            
            all_tasks = self.task_service.get_all_active()
            other_tasks = [t for t in all_tasks if t.id != self.entity_id]
            self.task_choices = {"Nenhuma": None}
            
            self.opt_dep = QComboBox()
            self.opt_dep.addItem("Nenhuma")
            for ot in other_tasks:
                name = f"{ot.id} - {ot.title}"
                self.task_choices[name] = ot.id
                self.opt_dep.addItem(name)
            layout.addWidget(self.opt_dep)
            
            layout.addWidget(QLabel("Força da Dependência:"))
            self.opt_dep_strength = QComboBox()
            self.opt_dep_strength.addItems(["obrigatória", "recomendada", "informativa"])
            layout.addWidget(self.opt_dep_strength)
            
        layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        btn_layout = QHBoxLayout()
        if self.agenda_item:
            self.btn_del = QPushButton("Excluir")
            self.btn_del.setObjectName("danger")
            self.btn_del.clicked.connect(self.delete)
            btn_layout.addWidget(self.btn_del)
            
        self.btn_save = QPushButton("Salvar Agendamento")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save)
        btn_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(btn_layout)
        
    def populate_fields(self):
        if self.agenda_item:
            if self.agenda_item.start_date:
                qd = QDate.fromString(self.agenda_item.start_date, "yyyy-MM-dd")
                if qd.isValid(): self.dp_start.setDate(qd)
            if self.agenda_item.end_date:
                qd = QDate.fromString(self.agenda_item.end_date, "yyyy-MM-dd")
                if qd.isValid(): self.dp_end.setDate(qd)
            self.ent_effort.setText(str(self.agenda_item.effort_hours))
            self.opt_status.setCurrentText(self.agenda_item.schedule_status)
            
        if self.entity_type == 'task':
            curr_deps = self.agenda_service.dep_repo.get_dependencies_for_task(self.entity_id)
            if curr_deps:
                for k, v in self.task_choices.items():
                    if v == curr_deps[0].depends_on_task_id:
                        self.opt_dep.setCurrentText(k)
                        self.opt_dep_strength.setCurrentText(getattr(curr_deps[0], "dependency_strength", "obrigatória"))
                        break
                        
    def save(self):
        start = self.dp_start.date().toString("yyyy-MM-dd")
        end = self.dp_end.date().toString("yyyy-MM-dd")
        
        try:
            effort = float(self.ent_effort.text().strip() or 0)
        except ValueError:
            QMessageBox.warning(self, "Aviso", "O esforço em horas deve ser um valor numérico.")
            return
            
        status = self.opt_status.currentText()
        
        if self.agenda_item:
            self.agenda_item.start_date = start
            self.agenda_item.end_date = end
            self.agenda_item.effort_hours = effort
            self.agenda_item.schedule_status = status
            self.agenda_service.update_schedule(self.agenda_item)
        else:
            self.agenda_item = self.agenda_service.create_schedule(
                self.entity_type, self.entity_id, start, end, effort, status
            )
            
        if self.entity_type == 'task':
            selected_dep = self.opt_dep.currentText()
            dep_id = self.task_choices.get(selected_dep)
            strength = self.opt_dep_strength.currentText()
            
            curr_deps = self.agenda_service.dep_repo.get_dependencies_for_task(self.entity_id)
            for d in curr_deps:
                self.agenda_service.remove_dependency(self.entity_id, d.depends_on_task_id)
                
            if dep_id:
                try:
                    self.agenda_service.add_dependency(self.entity_id, dep_id, "finish_to_start", strength)
                except ValueError as ve:
                    QMessageBox.warning(self, "Erro de Dependência", str(ve))
                    
        event_bus.emit("entity_updated")
        if self.on_save:
            self.on_save()
        self.accept()
        
    def delete(self):
        reply = QMessageBox.question(self, 'Excluir', 'Deseja remover este período agendado?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.entity_type == 'task':
                curr_deps = self.agenda_service.dep_repo.get_dependencies_for_task(self.entity_id)
                for d in curr_deps:
                    self.agenda_service.remove_dependency(self.entity_id, d.depends_on_task_id)
            self.agenda_service.delete_schedule(self.agenda_item.id)
            event_bus.emit("entity_updated")
            if self.on_save:
                self.on_save()
            self.accept()
