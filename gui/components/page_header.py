from PySide6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel,
                               QWidget, QSizePolicy)
from PySide6.QtCore import Qt
from gui.theme import TEXT_SECONDARY, FONT_BODY_LG


class _Spacing(QWidget):
    """Espacador fixo. Substitui addSpacing(), que nao sobrevive a um
    layout reordenado."""

    def __init__(self, width):
        super().__init__()
        self.setFixedWidth(width)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)


class PageHeader(QFrame):
    def __init__(self, title="", subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("pageHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._left_layout = QHBoxLayout()
        self._left_layout.setSpacing(8)
        layout.addLayout(self._left_layout)

        text_area = QVBoxLayout()
        text_area.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("header")
        text_area.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_BODY_LG}px; padding: 0; border: none;"
        )
        self.subtitle_label.setVisible(bool(subtitle))
        text_area.addWidget(self.subtitle_label)

        self._left_layout.addLayout(text_area, stretch=1)

        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(8)
        layout.addLayout(self._button_layout)

        # Area livre a direita dos botoes, para paineis (referencias, filtros)
        self._right_layout = QHBoxLayout()
        self._right_layout.setSpacing(12)
        layout.addLayout(self._right_layout)
        self._right_layout.addStretch()

    def set_title(self, title: str):
        self.title_label.setText(title)

    def set_subtitle(self, subtitle: str):
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def add_left_widget(self, widget):
        self._left_layout.insertWidget(0, widget)

    def add_button(self, button):
        self._button_layout.addWidget(button)

    def add_right_widget(self, widget, spacing=12):
        """Painel a direita dos botoes (ex.: painel de referencias)."""
        if self._right_layout.count() > 1:
            # substitui o stretch inicial por espacamento explicito
            self._right_layout.insertWidget(self._right_layout.count() - 1, widget)
        else:
            self._right_layout.addWidget(widget)
        if spacing:
            self._right_layout.insertWidget(self._right_layout.count() - 1,
                                            _Spacing(spacing))
