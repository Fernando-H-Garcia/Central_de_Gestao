from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QPushButton, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt
from models.entities import Idea
from services.project_service import ProjectService

class PromoteIdeaDialogQt(QDialog):
    def __init__(self, parent=None, idea: Idea = None, default_type="project", on_promote=None):
        super().__init__(parent)
        self.idea = idea
        self.on_promote = on_promote
        self.project_service = ProjectService()
        self.projects = self.project_service.get_all_active()
        
        self.setWindowTitle("Promover Ideia")
        self.resize(400, 500)
        self.default_type = default_type
        
        self.setup_ui()
        self.populate_fields()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        main_layout.addWidget(QLabel("Transformar em:"))
        self.opt_type = QComboBox()
        self.opt_type.addItems(["Projeto", "Tarefa"])
        self.opt_type.currentTextChanged.connect(self.on_type_changed)
        main_layout.addWidget(self.opt_type)
        
        self.lbl_project = QLabel("Projeto Destino (para a Tarefa):")
        main_layout.addWidget(self.lbl_project)
        self.opt_project = QComboBox()
        self.opt_project.addItem("Nenhum", None)
        for p in self.projects:
            self.opt_project.addItem(p.name, p.id)
        main_layout.addWidget(self.opt_project)
        
        main_layout.addWidget(QLabel("Novo Título:"))
        self.ent_title = QLineEdit()
        main_layout.addWidget(self.ent_title)
        
        main_layout.addWidget(QLabel("Nova Descrição:"))
        self.ent_desc = QTextEdit()
        main_layout.addWidget(self.ent_desc)
        
        self.chk_keep_linked = QCheckBox("Manter Ideia vinculada")
        self.chk_keep_linked.setChecked(True)
        main_layout.addWidget(self.chk_keep_linked)
        
        self.chk_copy_tags = QCheckBox("Copiar Tags/Arquivos")
        self.chk_copy_tags.setChecked(True)
        main_layout.addWidget(self.chk_copy_tags)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Promover")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self.promote)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        
        main_layout.addLayout(btn_layout)
        
    def populate_fields(self):
        if self.default_type == "task":
            self.opt_type.setCurrentText("Tarefa")
        else:
            self.opt_type.setCurrentText("Projeto")
            
        if self.idea:
            self.ent_title.setText(self.idea.title or "")
            self.ent_desc.setText(self.idea.description or "")
            if self.idea.project_id:
                idx = self.opt_project.findData(self.idea.project_id)
                if idx >= 0:
                    self.opt_project.setCurrentIndex(idx)
                    
        self.on_type_changed(self.opt_type.currentText())

    def on_type_changed(self, text):
        if text == "Tarefa":
            self.lbl_project.show()
            self.opt_project.show()
        else:
            self.lbl_project.hide()
            self.opt_project.hide()

    def promote(self):
        title = self.ent_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Aviso", "O título é obrigatório.")
            return
            
        data = {
            "type": "project" if self.opt_type.currentText() == "Projeto" else "task",
            "title": title,
            "description": self.ent_desc.toPlainText(),
            "keep_linked": self.chk_keep_linked.isChecked(),
            "copy_tags": self.chk_copy_tags.isChecked(),
            "project_id": self.opt_project.currentData() if self.opt_type.currentText() == "Tarefa" else None
        }
        
        if self.on_promote:
            self.on_promote(data)
        self.accept()
