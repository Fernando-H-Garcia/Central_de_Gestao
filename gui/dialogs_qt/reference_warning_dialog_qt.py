from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class ReferenceWarningDialog(QDialog):
    """Dialog that shows impact analysis before deleting a referenced entity."""

    def __init__(self, entity_type_label: str, entity_name: str, references: list, parent=None, show_archive=True):
        """
        :param entity_type_label: e.g. "tarefa", "projeto", "documento", "arquivo"
        :param entity_name: the title/name of the entity being deleted
        :param references: list of dicts with keys "type_label" and "title"
        :param show_archive: whether to show the "Arquivar" button
        """
        super().__init__(parent)
        self.action = None  # "archive", "delete_all", None
        self.references = references
        self.show_archive = show_archive

        self.setWindowTitle("ATENÇÃO!")
        self.setMinimumWidth(520)
        self.setModal(True)
        self.setup_ui(entity_type_label, entity_name, references)

    def setup_ui(self, entity_type_label: str, entity_name: str, references: list):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(12)

        # ── Header: icon + ATENÇÃO ──
        header = QHBoxLayout()
        header.setSpacing(10)

        icon_label = QLabel("\u26a0\ufe0f")  # yellow warning emoji
        icon_font = QFont()
        icon_font.setPointSize(28)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignCenter)
        header.addWidget(icon_label)

        title_label = QLabel("ATENÇÃO!")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #e3a84a;")
        header.addWidget(title_label, stretch=1)
        main.addLayout(header)

        # ── Subtitle ──
        subtitle = QLabel("Impacto da Exclusão")
        sf = QFont()
        sf.setPointSize(14)
        subtitle.setFont(sf)
        subtitle.setStyleSheet("color: #ccc;")
        main.addWidget(subtitle)

        # ── Entity description ──
        entity_line = QLabel(
            f'O item ({entity_type_label}) "<b>{entity_name}</b>" '
            f'é referenciado por:'
        )
        entity_line.setWordWrap(True)
        entity_line.setStyleSheet("color: #ddd; font-size: 13px;")
        main.addWidget(entity_line)

        # ── Reference list (scroll) ──
        if references:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet("QScrollArea { background: transparent; }")

            list_widget = QWidget()
            list_widget.setStyleSheet("background: transparent;")
            list_layout = QVBoxLayout(list_widget)
            list_layout.setContentsMargins(0, 0, 0, 0)
            list_layout.setSpacing(6)

            for ref in references:
                ref_frame = QFrame()
                ref_frame.setStyleSheet("""
                    QFrame {
                        background-color: #1c1c2e;
                        border: 1px solid #2a2a3f;
                        border-radius: 6px;
                        padding: 8px 12px;
                    }
                """)
                ref_row = QHBoxLayout(ref_frame)
                ref_row.setContentsMargins(0, 0, 0, 0)
                type_lbl = QLabel(ref["type_label"])
                type_lbl.setStyleSheet("color: #4a6fe3; font-weight: bold; font-size: 12px;")
                type_lbl.setFixedWidth(110)
                ref_row.addWidget(type_lbl)
                name_lbl = QLabel(ref["title"])
                name_lbl.setStyleSheet("color: #fff; font-size: 12px;")
                name_lbl.setWordWrap(True)
                ref_row.addWidget(name_lbl, stretch=1)
                list_layout.addWidget(ref_frame)

            list_layout.addStretch()
            scroll.setWidget(list_widget)
            main.addWidget(scroll, stretch=1)

        # ── Warning note ──
        note = QLabel(
            "Excluir irá remover todas as referências existentes definitivamente."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #e3a84a; font-size: 12px; font-style: italic;")
        main.addWidget(note)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_archive = QPushButton("📦 Arquivar")
        btn_archive.setStyleSheet("""
            QPushButton {
                padding: 8px 20px; border-radius: 5px; font-weight: bold; font-size: 13px;
                background-color: #2a2a3f; color: #fff; border: 1px solid #555;
            }
            QPushButton:hover { background-color: #3a3a5f; }
        """)
        btn_archive.clicked.connect(lambda: self._choose("archive"))
        if self.show_archive:
            btn_row.addWidget(btn_archive)

        btn_row.addStretch()

        btn_delete = QPushButton("🗑️ Excluir tudo")
        btn_delete.setStyleSheet("""
            QPushButton {
                padding: 8px 20px; border-radius: 5px; font-weight: bold; font-size: 13px;
                background-color: #e53935; color: #fff; border: none;
            }
            QPushButton:hover { background-color: #ff5252; }
        """)
        btn_delete.clicked.connect(lambda: self._choose("delete_all"))
        btn_row.addWidget(btn_delete)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("""
            QPushButton {
                padding: 8px 20px; border-radius: 5px; font-weight: bold; font-size: 13px;
                background-color: transparent; color: #aaa; border: 1px solid #555;
            }
            QPushButton:hover { background-color: #2d2d55; color: #fff; border: 1px solid #4a6fe3; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        main.addLayout(btn_row)

    def _choose(self, action: str):
        self.action = action
        self.accept()
