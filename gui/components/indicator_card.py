from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from gui.theme import TEXT_PRIMARY, TEXT_SECONDARY, BG_CARD, RADIUS_LG, FONT_BODY, FONT_TITLE


class IndicatorCard(QFrame):
    def __init__(self, icon="", number="", description="", color=None, parent=None):
        super().__init__(parent)
        self.setObjectName("indicatorCard")

        accent = color or TEXT_PRIMARY

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        if icon:
            self.icon_label = QLabel(icon)
            self.icon_label.setStyleSheet(
                f"font-size: 20px; padding: 0; border: none;"
            )
            layout.addWidget(self.icon_label)

        self.number_label = QLabel(str(number))
        self.number_label.setStyleSheet(
            f"font-size: {FONT_TITLE}px; font-weight: bold; color: {accent}; padding: 0; border: none;"
        )
        layout.addWidget(self.number_label)

        self.desc_label = QLabel(description)
        self.desc_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_BODY}px; padding: 0; border: none;"
        )
        layout.addWidget(self.desc_label)

        layout.addStretch()

        self.setStyleSheet(f"""
            QFrame#indicatorCard {{
                background-color: {BG_CARD};
                border-radius: {RADIUS_LG}px;
                border: none;
            }}
        """)

    def set_number(self, number):
        self.number_label.setText(str(number))
