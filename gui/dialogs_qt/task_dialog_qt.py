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
        from services.task_service import TaskService
        self.task_svc = TaskService()
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
        
        # Parent Task
        layout.addWidget(QLabel("Tarefa Pai:"))
        self.opt_parent_task = QComboBox()
        self.parent_task_dict = {}
        self._populate_parent_tasks()
        self.opt_proj.currentIndexChanged.connect(self._on_project_changed)
        layout.addWidget(self.opt_parent_task)
        
        # Dates
        layout.addWidget(QLabel("Data Início:"))
        self.ent_start = QDateEdit()
        self.ent_start.setCalendarPopup(True)
        self.ent_start.setDate(QDate.currentDate())
        style_calendar_today(self.ent_start)
        layout.addWidget(self.ent_start)

        # Milestone Checkbox (antes da data final — marco não tem prazo)
        self.chk_milestone = QCheckBox("É um Marco (Milestone - Sem duração/esforço)")
        self.chk_milestone.setStyleSheet("""
            QCheckBox { color: #ffffff; }
            QCheckBox::indicator {
                width: 15px; height: 15px;
                border: 1px solid #9a9ab8; border-radius: 3px;
                background-color: #2a2a3f;
            }
            QCheckBox::indicator:checked {
                background-color: #4a6fe3; border-color: #6a8fe3;
            }
        """)
        layout.addWidget(self.chk_milestone)

        layout.addWidget(QLabel("Data Fim (Prazo):"))
        self.ent_due = QDateEdit()
        self.ent_due.setCalendarPopup(True)
        self.ent_due.setDate(QDate.currentDate())
        self.ent_due.setStyleSheet("""
            QDateEdit:disabled {
                background-color: #3a3a4a;
                color: #b0b0c8;
            }
        """)
        style_calendar_today(self.ent_due)
        layout.addWidget(self.ent_due)

        # Estimated Hours
        layout.addWidget(QLabel("Esforço Estimado (Horas):"))
        self.ent_estimated_hours = QLineEdit("0.0")
        layout.addWidget(self.ent_estimated_hours)

        # Regras: só FILHA de pai não-marco é bloqueada (tarefa raiz pode ser Marco);
        # Marco não tem data final (só a data do marco)
        self.opt_parent_task.currentIndexChanged.connect(self._on_parent_changed)
        self.chk_milestone.toggled.connect(self._on_milestone_toggled)
        self.ent_start.dateChanged.connect(self._sync_milestone_due)

        layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Save Button
        self.btn_save = QPushButton("Salvar Tarefa")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save)
        main_layout.addWidget(self.btn_save)
        
    def _selected_project_id(self):
        proj_sel = self.opt_proj.currentText()
        return self.proj_dict.get(proj_sel)

    def _selected_parent(self):
        pid = self.parent_task_dict.get(self.opt_parent_task.currentText())
        if pid is None:
            return None
        try:
            return self.task_svc.task_repo.get_by_id(pid)
        except Exception:
            return None

    def _on_parent_changed(self):
        """Só FILHA de pai não-marco é bloqueada — tarefa raiz (sem pai) pode ser Marco."""
        parent = self._selected_parent()
        if parent is None:
            parent_is_ms = True   # raiz: sempre pode
        else:
            parent_is_ms = bool(getattr(parent, "is_milestone", False))
        if not parent_is_ms:
            self.chk_milestone.setChecked(False)
        self.chk_milestone.setEnabled(parent_is_ms)
        self.chk_milestone.setToolTip(
            "" if parent_is_ms else "Somente disponível se a Tarefa Pai também for um Marco"
        )

    def _on_milestone_toggled(self, checked):
        """Marco não tem data final — apenas a data do marco."""
        self.ent_due.setEnabled(not checked)
        if checked:
            self.ent_due.setDate(self.ent_start.date())

    def _sync_milestone_due(self):
        if self.chk_milestone.isChecked():
            self.ent_due.setDate(self.ent_start.date())

    def _on_project_changed(self):
        self._populate_parent_tasks()
        self._on_parent_changed()

    def _populate_parent_tasks(self):
        self.opt_parent_task.blockSignals(True)
        current = self.opt_parent_task.currentText()
        self.opt_parent_task.clear()
        self.parent_task_dict = {"Nenhuma": None}
        self.opt_parent_task.addItem("Nenhuma")

        proj_id = self._selected_project_id()
        exclude_ids = set()
        if self.task:
            exclude_ids.add(self.task.id)
            try:
                exclude_ids.update(self.task_svc.get_descendant_ids(self.task.id))
            except Exception:
                pass

        all_tasks = self.task_svc.get_all_active()
        for t in all_tasks:
            if t.id in exclude_ids:
                continue
            if proj_id is not None and t.project_id != proj_id:
                continue
            name = f"{t.id} - {t.title}"
            self.parent_task_dict[name] = t.id
            self.opt_parent_task.addItem(name)

        if current and current in self.parent_task_dict:
            self.opt_parent_task.setCurrentText(current)
        self.opt_parent_task.blockSignals(False)

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
                        
            if getattr(self.task, "parent_task_id", None):
                for k, v in self.parent_task_dict.items():
                    if v == self.task.parent_task_id:
                        self.opt_parent_task.setCurrentText(k)
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
        # aplica as regras de Marco (habilitar/desabilitar) após popular
        self._on_parent_changed()
        self._on_milestone_toggled(self.chk_milestone.isChecked())
            
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
        
        parent_sel = self.opt_parent_task.currentText()
        parent_id = self.parent_task_dict.get(parent_sel)
        
        start_date = self.ent_start.date().toString("yyyy-MM-dd")
        due_date = self.ent_due.date().toString("yyyy-MM-dd")
        
        try:
            est_hours = float(self.ent_estimated_hours.text().strip() or 0.0)
        except ValueError:
            est_hours = 0.0
            
        is_ms = self.chk_milestone.isChecked()
        if is_ms:
            # marco não tem prazo: data final = data do marco
            due_date = start_date
        
        if self.task:
            import copy
            original_task = copy.deepcopy(self.task)
            self.task.title = title
            self.task.context = context
            self.task.status = status
            self.task.energy_level = energy
            self.task.project_id = proj_id
            self.task.parent_task_id = parent_id
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
                parent_task_id=parent_id,
                start_date=start_date, due_date=due_date, estimated_hours=est_hours, 
                is_milestone=is_ms
            )
            if self.on_save:
                self.on_save(new_task, True, None)
                
        self.accept()
