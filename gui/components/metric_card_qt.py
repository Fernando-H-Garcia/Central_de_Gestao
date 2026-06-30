from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from gui.theme import BG_CARD, BG_HOVER, BORDER_SUBTLE, BORDER_FOCUS, TEXT_SECONDARY, RADIUS_MD


class MetricCardQt(QFrame):
    clicked = Signal(str) # Emits the title of the card

    def __init__(self, title, count, color, icon="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.color = color
        self.is_active = False

        self.setCursor(QCursor(Qt.PointingHandCursor))

        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(2)

        if icon:
            self.lbl_icon = QLabel(icon)
            self.lbl_icon.setAlignment(Qt.AlignCenter)
            self.lbl_icon.setStyleSheet("font-size: 18px; padding: 0; border: none;")
            card_layout.addWidget(self.lbl_icon)

        self.lbl_count = QLabel(str(count))
        self.lbl_count.setAlignment(Qt.AlignCenter)
        self.lbl_count.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {self.color}; padding: 0; border: none;")

        self.lbl_title = QLabel(self.title)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; padding: 0; border: none;")

        card_layout.addWidget(self.lbl_count)
        card_layout.addWidget(self.lbl_title)

        self.update_style()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()

    def update_style(self, hover=False):
        if self.is_active:
            bg = BG_HOVER
            border = f"1px solid {self.color}"
        elif hover:
            bg = BG_HOVER
            border = f"1px solid {BORDER_FOCUS}"
        else:
            bg = BG_CARD
            border = f"1px solid transparent"

        self.setStyleSheet(f"""
            MetricCardQt {{
                background-color: {bg};
                border-radius: {RADIUS_MD}px;
                border: {border};
            }}
        """)

    def update_count(self, count):
        self.lbl_count.setText(str(count))

    def enterEvent(self, event):
        self.update_style(hover=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update_style(hover=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.title)
        super().mousePressEvent(event)
