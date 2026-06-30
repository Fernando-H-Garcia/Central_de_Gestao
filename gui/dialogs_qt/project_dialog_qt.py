from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QMessageBox, QDateEdit,
    QTabWidget, QWidget, QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, QDate
from models.entities import Project
import copy
from core.event_bus import event_bus
from gui.theme import set_combobox_colors, ENERGY_COLORS, apply_combobox_dynamic_color, get_energy_color, style_calendar_today

class ProjectDialogQt(QDialog):
    def __init__(self, parent=None, project: Project = None, on_save=None):
        super().__init__(parent)
        self.project = project
        self.on_save = on_save
        self._saved_project_id = project.id if project else None

        self.setWindowTitle("Criação de Projeto" if not project else "Editor de Projeto")
        self.resize(520, 480)

        self.setup_ui()
        self.populate_fields()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()

        # ── Aba: Dados Gerais ─────────────────────────────────────────
        tab_geral = QWidget()
        layout = QVBoxLayout(tab_geral)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Name
        layout.addWidget(QLabel("Nome do Projeto:"))
        self.ent_name = QLineEdit()
        layout.addWidget(self.ent_name)

        # Objective
        layout.addWidget(QLabel("Objetivo:"))
        self.ent_obj = QLineEdit()
        layout.addWidget(self.ent_obj)

        # Priority
        layout.addWidget(QLabel("Prioridade:"))
        self.opt_prio = QComboBox()
        self.opt_prio.addItems(["Baixa", "Média", "Alta", "Crítica"])
        set_combobox_colors(self.opt_prio, ENERGY_COLORS)
        apply_combobox_dynamic_color(self.opt_prio, get_energy_color)
        layout.addWidget(self.opt_prio)

        # Due Date
        layout.addWidget(QLabel("Prazo:"))
        self.ent_due = QDateEdit()
        self.ent_due.setCalendarPopup(True)
        self.ent_due.setDate(QDate.currentDate())
        style_calendar_today(self.ent_due)
        layout.addWidget(self.ent_due)

        layout.addStretch()
        self.tabs.addTab(tab_geral, "Dados Gerais")

        # ── Aba: Referências ──────────────────────────────────────────
        tab_refs = QWidget()
        refs_layout = QVBoxLayout(tab_refs)
        refs_layout.setContentsMargins(16, 16, 16, 16)

        from gui.components.references_panel_qt import ReferencesPanelQt
        self.refs_panel = ReferencesPanelQt(
            entity_type="project",
            entity_id=self._saved_project_id or 0,
            parent=self
        )
        refs_layout.addWidget(self.refs_panel)
        self.tabs.addTab(tab_refs, "Referências")

        main_layout.addWidget(self.tabs)

        # ── Botões ────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Salvar")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        main_layout.addLayout(btn_layout)

    def populate_fields(self):
        if self.project:
            self.ent_name.setText(self.project.name)
            if self.project.objective:
                self.ent_obj.setText(self.project.objective)
            self.opt_prio.setCurrentText(self.project.priority)
            if self.project.due_date:
                due_date_str = str(self.project.due_date).split(' ')[0]
                qdate = QDate.fromString(due_date_str, "yyyy-MM-dd")
                if qdate.isValid():
                    self.ent_due.setDate(qdate)
        else:
            self.opt_prio.setCurrentText("Média")

    def save(self):
        name = self.ent_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Aviso", "O nome do projeto é obrigatório.")
            return

        obj = self.ent_obj.text().strip()
        prio = self.opt_prio.currentText()
        due_date = self.ent_due.date().toString("yyyy-MM-dd")

        if self.project:
            original_project = copy.deepcopy(self.project)
            self.project.name = name
            self.project.objective = obj
            self.project.priority = prio
            self.project.due_date = due_date
            if self.on_save:
                self.on_save(self.project, False, original_project)
            # Atualiza painel de referências com ID real
            if self.project.id:
                self.refs_panel.set_entity("project", self.project.id)
        else:
            new_proj = Project(name=name, objective=obj, priority=prio, due_date=due_date)
            if self.on_save:
                self.on_save(new_proj, True, None)
            # Se o projeto foi criado e tem ID, atualiza painel
            if new_proj.id:
                self.refs_panel.set_entity("project", new_proj.id)

        self.accept()
