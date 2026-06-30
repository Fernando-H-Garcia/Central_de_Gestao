from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QPushButton, QMessageBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from models.entities import Idea
from services.project_service import ProjectService
from gui.theme import set_combobox_colors, STATUS_COLORS, ENERGY_COLORS, apply_combobox_dynamic_color, get_status_color, get_energy_color

class IdeaDialogQt(QDialog):
    def __init__(self, parent=None, idea: Idea = None, on_save=None, project_id=None, task_id=None):
        super().__init__(parent)
        self.idea = idea
        self.on_save = on_save
        self._preselected_project_id = project_id
        self._preselected_task_id = task_id
        self.project_service = ProjectService()
        self.projects = self.project_service.get_all_active()
        
        self.setWindowTitle("Nova Ideia" if not idea else "Editar Ideia")
        self.resize(500, 600)
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
        
        layout.addWidget(QLabel("Título:"))
        self.ent_title = QLineEdit()
        layout.addWidget(self.ent_title)
        
        layout.addWidget(QLabel("Categoria:"))
        self.opt_category = QComboBox()
        self.opt_category.addItems(["Geral", "Melhoria", "Nova Funcionalidade", "Pesquisa", "Inovação"])
        layout.addWidget(self.opt_category)
        
        layout.addWidget(QLabel("Projeto Vinculado:"))
        self.opt_project = QComboBox()
        self.opt_project.addItem("Nenhum", None)
        for p in self.projects:
            self.opt_project.addItem(p.name, p.id)
        layout.addWidget(self.opt_project)
        
        layout.addWidget(QLabel("Status:"))
        self.opt_status = QComboBox()
        self.opt_status.addItems(["Pendente", "Em Andamento", "Pausado", "Aguardando", "Bloqueado", "Concluído"])
        layout.addWidget(self.opt_status)
        
        layout.addWidget(QLabel("Prioridade:"))
        self.opt_priority = QComboBox()
        self.opt_priority.addItems(["Baixa", "Média", "Alta", "Crítica"])
        layout.addWidget(self.opt_priority)
        
        set_combobox_colors(self.opt_status, STATUS_COLORS)
        set_combobox_colors(self.opt_priority, ENERGY_COLORS)
        
        self.opt_status.currentIndexChanged.connect(lambda: apply_combobox_dynamic_color(self.opt_status, get_status_color))
        self.opt_priority.currentIndexChanged.connect(lambda: apply_combobox_dynamic_color(self.opt_priority, get_energy_color))
        
        layout.addWidget(QLabel("Descrição:"))
        self.ent_desc = QTextEdit()
        layout.addWidget(self.ent_desc)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Salvar")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self.save_idea)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        
        main_layout.addLayout(btn_layout)
        
    def populate_fields(self):
        if not self.idea:
            self.opt_status.setCurrentText("Pendente")
            self.opt_priority.setCurrentText("Média")
            if self._preselected_project_id:
                idx = self.opt_project.findData(self._preselected_project_id)
                if idx >= 0:
                    self.opt_project.setCurrentIndex(idx)
        else:
            self.ent_title.setText(self.idea.title or "")
            self.opt_category.setCurrentText(self.idea.category or "Geral")
            self.opt_status.setCurrentText(self.idea.status or "Pendente")
            self.opt_priority.setCurrentText(self.idea.priority or "Média")
            self.ent_desc.setText(self.idea.description or "")
            if self.idea.project_id:
                idx = self.opt_project.findData(self.idea.project_id)
                if idx >= 0:
                    self.opt_project.setCurrentIndex(idx)
                    
        apply_combobox_dynamic_color(self.opt_status, get_status_color)
        apply_combobox_dynamic_color(self.opt_priority, get_energy_color)

    def save_idea(self):
        title = self.ent_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Aviso", "O título é obrigatório.")
            return
            
        data = {
            "title": title,
            "category": self.opt_category.currentText(),
            "status": self.opt_status.currentText(),
            "priority": self.opt_priority.currentText(),
            "description": self.ent_desc.toPlainText(),
            "project_id": self.opt_project.currentData(),
        }
        if self._preselected_task_id:
            data["task_id"] = self._preselected_task_id
        
        if self.on_save:
            self.on_save(data)
        self.accept()
