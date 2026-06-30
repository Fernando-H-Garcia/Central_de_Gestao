from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from gui.theme import (
    BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY,
    SUCCESS_GREEN, ACCENT_BLUE, WARNING_ORANGE, ERROR_RED,
    RADIUS_SM, FONT_BODY, FONT_CAPTION
)


class ProgressBar(QWidget):
    def __init__(self, value=0, maximum=100, parent=None):
        super().__init__(parent)
        self._value = value
        self._maximum = maximum
        self.setFixedHeight(20)
        self.setMinimumWidth(100)

    def set_value(self, value: int):
        self._value = max(0, min(value, self._maximum))
        self.update()

    def set_maximum(self, maximum: int):
        self._maximum = max(1, maximum)
        self.update()

    def value(self) -> int:
        return self._value

    def percentage(self) -> float:
        return (self._value / self._maximum) * 100

    def _bar_color(self) -> str:
        pct = self.percentage()
        if pct >= 100:
            return SUCCESS_GREEN
        if pct >= 70:
            return ACCENT_BLUE
        if pct >= 40:
            return WARNING_ORANGE
        return ERROR_RED

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        bg_color = QColor(BG_CARD)
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, RADIUS_SM, RADIUS_SM)

        pct = self.percentage()
        fill_w = int(w * (pct / 100))
        if fill_w > 0:
            bar_color = QColor(self._bar_color())
            painter.setBrush(bar_color)
            painter.drawRoundedRect(0, 0, fill_w, h, RADIUS_SM, RADIUS_SM)

        painter.end()

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(120, 20)


class ProgressBarWithLabel(QWidget):
    def __init__(self, value=0, maximum=100, label="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if label:
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_BODY}px;")
            layout.addWidget(lbl)

        self.bar = ProgressBar(value, maximum)
        layout.addWidget(self.bar, stretch=1)

        self.pct_label = QLabel(f"{self.bar.percentage():.0f}%")
        self.pct_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {FONT_CAPTION}px; font-weight: bold;")
        self.pct_label.setFixedWidth(36)
        layout.addWidget(self.pct_label)

    def set_value(self, value: int):
        self.bar.set_value(value)
        self.pct_label.setText(f"{self.bar.percentage():.0f}%")
