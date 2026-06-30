import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt
from services.task_service import TaskService
from services.project_service import ProjectService
from services.agenda_service import AgendaService
from database.connection import get_db_cursor
from gui.components.page_header import PageHeader
from gui.components.indicator_card import IndicatorCard
from gui.theme import ACCENT_BLUE, WARNING_ORANGE, SUCCESS_GREEN, ERROR_RED, FONT_SUBTITLE, FONT_BODY

class WorkbenchQt(QWidget):
    def __init__(self):
        super().__init__()
        self.task_service = TaskService()
        self.project_service = ProjectService()
        self.agenda_service = AgendaService()
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header = PageHeader("Meu Dia")
        main_layout.addWidget(header)
        
        # Dashboard Cards Area
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(16)
        main_layout.addLayout(self.cards_layout)
        
        # Content Area with columns
        content_layout = QHBoxLayout()
        
        # Left Column (e.g., Tarefas)
        self.left_col_scroll = QScrollArea()
        self.left_col_scroll.setWidgetResizable(True)
        self.left_col_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.left_col_widget = QWidget()
        self.left_col_widget.setStyleSheet("background-color: transparent;")
        self.left_col_layout = QVBoxLayout(self.left_col_widget)
        self.left_col_scroll.setWidget(self.left_col_widget)
        
        # Right Column (e.g., Projetos/Agenda)
        self.right_col_scroll = QScrollArea()
        self.right_col_scroll.setWidgetResizable(True)
        self.right_col_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.right_col_widget = QWidget()
        self.right_col_widget.setStyleSheet("background-color: transparent;")
        self.right_col_layout = QVBoxLayout(self.right_col_widget)
        self.right_col_scroll.setWidget(self.right_col_widget)
        
        content_layout.addWidget(self.left_col_scroll)
        content_layout.addWidget(self.right_col_scroll)
        
        main_layout.addLayout(content_layout, stretch=1)
        
    def _create_section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size: {FONT_SUBTITLE}px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;")
        return lbl

    def _create_item_label(self, text):
        lbl = QLabel(f"• {text}")
        lbl.setStyleSheet(f"font-size: {FONT_BODY}px; padding: 6px 10px; background-color: #1c1c2e; border-radius: 5px; margin-bottom: 2px;")
        return lbl
        
    def load_data(self):
        active_projects = self.project_service.get_all_active()
        
        with get_db_cursor() as cursor:
            # Overdue tasks
            cursor.execute("SELECT title FROM tasks WHERE status != 'Concluído' AND is_archived = 0 AND deleted_at IS NULL AND due_date IS NOT NULL AND date(due_date) < date('now')")
            overdue_tasks = [row['title'] for row in cursor.fetchall()]
            
            # Today tasks
            cursor.execute("SELECT title FROM tasks WHERE status != 'Concluído' AND is_archived = 0 AND deleted_at IS NULL AND due_date IS NOT NULL AND date(due_date) = date('now')")
            today_tasks = [row['title'] for row in cursor.fetchall()]
            
            # In progress
            cursor.execute("SELECT title FROM tasks WHERE status = 'Em Andamento' AND is_archived = 0 AND deleted_at IS NULL")
            in_progress_tasks = [row['title'] for row in cursor.fetchall()]
            
            # Completed in last 7 days
            cursor.execute("SELECT count(*) FROM tasks WHERE status = 'Concluído' AND is_archived = 0 AND deleted_at IS NULL AND completed_at >= date('now', '-7 days')")
            row = cursor.fetchone()
            completed_week = row[0] if row else 0

        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Populate Dashboard Cards
        self.cards_layout.addWidget(IndicatorCard("📁", len(active_projects), "Projetos Ativos", ACCENT_BLUE))
        self.cards_layout.addWidget(IndicatorCard("📌", len(today_tasks), "Tarefas Hoje", SUCCESS_GREEN))
        self.cards_layout.addWidget(IndicatorCard("⚠️", len(overdue_tasks), "Atrasadas", ERROR_RED))
        self.cards_layout.addWidget(IndicatorCard("⏳", len(in_progress_tasks), "Em Andamento", WARNING_ORANGE))
        self.cards_layout.addWidget(IndicatorCard("✅", completed_week, "Concluídas Semana", SUCCESS_GREEN))
        
        # Clear existing lists
        while self.left_col_layout.count():
            item = self.left_col_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.right_col_layout.count():
            item = self.right_col_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Populate Left Column Lists
        self.left_col_layout.addWidget(self._create_section_title("🔴 Tarefas Atrasadas"))
        for t in overdue_tasks[:10]:
            self.left_col_layout.addWidget(self._create_item_label(t))
        if not overdue_tasks:
            self.left_col_layout.addWidget(QLabel("Nenhuma tarefa atrasada."))
            
        self.left_col_layout.addWidget(self._create_section_title("🟢 Tarefas para Hoje"))
        for t in today_tasks[:10]:
            self.left_col_layout.addWidget(self._create_item_label(t))
        if not today_tasks:
            self.left_col_layout.addWidget(QLabel("Nenhuma tarefa para hoje."))
            
        self.left_col_layout.addStretch()

        # Populate Right Column Lists
        self.right_col_layout.addWidget(self._create_section_title("⏳ Em Andamento"))
        for t in in_progress_tasks[:10]:
            self.right_col_layout.addWidget(self._create_item_label(t))
        if not in_progress_tasks:
            self.right_col_layout.addWidget(QLabel("Nenhuma tarefa em andamento."))
            
        self.right_col_layout.addWidget(self._create_section_title("📁 Projetos Ativos"))
        for p in active_projects[:10]:
            self.right_col_layout.addWidget(self._create_item_label(p.name))
        if not active_projects:
            self.right_col_layout.addWidget(QLabel("Nenhum projeto ativo."))
            
        self.right_col_layout.addStretch()
