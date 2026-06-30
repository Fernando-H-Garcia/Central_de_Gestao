from PySide6.QtWidgets import QPushButton
from gui.theme import (
    ACCENT_BLUE, ACCENT_ACTIVE, BG_CARD, BG_HOVER,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER_SUBTLE, BORDER_FOCUS,
    RADIUS_SM, FONT_BODY_LG
)


class PrimaryButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("primary")
        self.setStyleSheet(f"""
            QPushButton#primary {{
                background-color: {ACCENT_BLUE};
                color: {TEXT_PRIMARY};
                border: none;
                border-radius: {RADIUS_SM}px;
                padding: 8px 20px;
                font-size: {FONT_BODY_LG}px;
                font-weight: bold;
            }}
            QPushButton#primary:hover {{
                background-color: {ACCENT_ACTIVE};
            }}
            QPushButton#primary:pressed {{
                background-color: {ACCENT_BLUE};
            }}
        """)


class SecondaryButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("secondary")
        self.setStyleSheet(f"""
            QPushButton#secondary {{
                background-color: transparent;
                color: {TEXT_SECONDARY};
                border: 1px solid #555555;
                border-radius: {RADIUS_SM}px;
                padding: 8px 20px;
                font-size: {FONT_BODY_LG}px;
            }}
            QPushButton#secondary:hover {{
                background-color: {BG_HOVER};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_FOCUS};
            }}
        """)


class TextButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {ACCENT_BLUE};
                border: none;
                border-radius: {RADIUS_SM}px;
                padding: 4px 8px;
                font-size: {FONT_BODY_LG}px;
            }}
            QPushButton:hover {{
                color: {ACCENT_ACTIVE};
                text-decoration: underline;
            }}
        """)
