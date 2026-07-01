from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from gui.theme import get_status_color, get_energy_color, get_archived_color, RADIUS_SM, TEXT_PRIMARY, FONT_CAPTION


class BadgeDelegate(QStyledItemDelegate):
    def __init__(self, mode="status", parent=None):
        super().__init__(parent)
        self._mode = mode

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        text = index.data(Qt.DisplayRole) or ""

        if text == "ARQUIVADO":
            color = get_archived_color()
        else:
            color = get_status_color(text) if self._mode == "status" else get_energy_color(text)

        bg_color = QColor(color)
        bg_color.setAlpha(50)
        border_color = QColor(color)
        border_color.setAlpha(100)

        rect = option.rect.adjusted(12, 4, -12, -4)
        if rect.width() < 10 or rect.height() < 4:
            painter.restore()
            return

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(rect, RADIUS_SM, RADIUS_SM)

        painter.setPen(QColor(color))
        font = QFont()
        font.setBold(True)
        font.setPointSize(FONT_CAPTION)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, text)

        painter.restore()

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        # Add 30px to account for the 12px left + 12px right padding plus a safety margin
        return QSize(base.width() + 30, max(base.height(), 26))
