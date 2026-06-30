from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QListWidget, QSplitter, QFrame,
    QListWidgetItem, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt
from services.note_service import NoteService
from models.entities import Note
from core.event_bus import event_bus
import copy

class NotesQt(QWidget):
    def __init__(self, project_id=None, task_id=None):
        super().__init__()
        self.service = NoteService()
        self.project_id = project_id
        self.task_id = task_id
        self.current_note = None
        
        self.setup_ui()
        self.load_data()
        
        self._snapshot_cb = lambda _: self.load_data()
        event_bus.subscribe("snapshot_updated", self._snapshot_cb)
        self.destroyed.connect(self._cleanup_snapshot)

    def _cleanup_snapshot(self):
        event_bus.unsubscribe("snapshot_updated", self._snapshot_cb)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setStyleSheet("background-color: #1c1c2e; border-radius: 10px;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        lbl_header = QLabel("📝 Notas")
        lbl_header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 5px;")
        sidebar_layout.addWidget(lbl_header)
        
        self.btn_new = QPushButton("＋ Nova Nota")
        self.btn_new.setStyleSheet("background-color: #6366f1; color: white; padding: 8px; font-weight: bold; border-radius: 5px;")
        self.btn_new.clicked.connect(self.new_note)
        sidebar_layout.addWidget(self.btn_new)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filtrar notas...")
        self.search_bar.setStyleSheet("padding: 5px; border-radius: 5px; background-color: #13131f; color: white; border: 1px solid #2a2a3f;")
        self.search_bar.textChanged.connect(self.load_data)
        sidebar_layout.addWidget(self.search_bar)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
            }
            QListWidget::item {
                padding: 10px;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #2d2d55;
                border-radius: 5px;
            }
        """)
        self.list_widget.itemClicked.connect(self.on_item_selected)
        sidebar_layout.addWidget(self.list_widget)
        
        # Editor Area
        self.editor_frame = QFrame()
        self.editor_frame.setStyleSheet("background-color: #13131f;")
        editor_layout = QVBoxLayout(self.editor_frame)
        
        self.lbl_title = QLabel("Selecione ou crie uma nota")
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        editor_layout.addWidget(self.lbl_title)
        
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("background-color: #1c1c2e; color: white; border: 1px solid #2a2a3f; border-radius: 5px; padding: 10px; font-size: 14px;")
        editor_layout.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Salvar Nota")
        self.btn_save.setObjectName("primary")
        self.btn_save.clicked.connect(self.save_note)
        
        self.btn_delete = QPushButton("Excluir Nota")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.clicked.connect(self.delete_note)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_save)
        editor_layout.addLayout(btn_layout)
        
        self.editor_frame.setEnabled(False)
        
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.editor_frame)
        splitter.setSizes([300, 700])
        main_layout.addWidget(splitter)
        
    def load_data(self):
        # Temporarily disconnect to avoid triggering events
        try:
            self.list_widget.itemClicked.disconnect(self.on_item_selected)
        except Exception:
            pass
        
        try:
            query = self.search_bar.text().lower()
        except RuntimeError:
            return
            
        notes = self.service.list()
        if self.project_id:
            notes = [n for n in notes if n.project_id == self.project_id]
        if self.task_id:
            notes = [n for n in notes if n.task_id == self.task_id]
            
        if query:
            notes = [n for n in notes if query in (n.content or "").lower()]
            
        self.list_widget.clear()
        
        for n in notes:
            # First line as title
            lines = (n.content or "").strip().split("\n")
            title = lines[0][:40] + "..." if lines and lines[0] else "Nota Vazia"
            
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, n)
            self.list_widget.addItem(item)
            
            if self.current_note and self.current_note.id == n.id:
                item.setSelected(True)
                
        self.list_widget.itemClicked.connect(self.on_item_selected)
        
    def on_item_selected(self, item):
        self.current_note = item.data(Qt.UserRole)
        self.editor_frame.setEnabled(True)
        self.lbl_title.setText(f"Editando Nota #{self.current_note.id}")
        self.text_edit.setPlainText(self.current_note.content or "")
        
    def new_note(self):
        self.current_note = None
        self.list_widget.clearSelection()
        self.editor_frame.setEnabled(True)
        self.lbl_title.setText("Nova Nota")
        self.text_edit.setPlainText("")
        self.text_edit.setFocus()
        
    def save_note(self):
        content = self.text_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Aviso", "A nota não pode estar vazia.")
            return
            
        if self.current_note:
            original = copy.deepcopy(self.current_note)
            self.current_note.content = content
            # Assuming update method exists in NoteService
            if hasattr(self.service, 'update'):
                self.service.update(self.current_note, original)
            else:
                self.service.repo.update(self.current_note)
                self.service._log(self.current_note.id, "UPDATED")
        else:
            note = Note(content=content, project_id=self.project_id, task_id=self.task_id)
            self.service.create(note)
            
        event_bus.emit("entity_updated")
        
    def delete_note(self):
        if not self.current_note:
            return
            
        reply = QMessageBox.question(self, "Confirmar", "Deseja mesmo excluir esta nota?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Assuming soft_delete or delete exists
            if hasattr(self.service, 'soft_delete'):
                self.service.soft_delete(self.current_note.id)
            elif hasattr(self.service, 'repo'):
                self.service.repo.soft_delete(self.current_note.id)
                self.service._log(self.current_note.id, "DELETED")
            
            self.current_note = None
            self.editor_frame.setEnabled(False)
            self.text_edit.setPlainText("")
            self.lbl_title.setText("Selecione ou crie uma nota")
            event_bus.emit("entity_updated")
