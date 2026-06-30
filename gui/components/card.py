from PySide6.QtWidgets import QFrame, QVBoxLayout
from gui.theme import BG_CARD, RADIUS_LG


class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)

    def layout(self):
        return self._layout

    @staticmethod
    def style() -> str:
        return f"""
            QFrame#card {{
                background-color: {BG_CARD};
                border-radius: {RADIUS_LG}px;
            }}
        """
