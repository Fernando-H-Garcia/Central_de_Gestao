from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from gui.theme import get_status_color, RADIUS_SM, TEXT_PRIMARY, FONT_CAPTION


class ProgressBarDelegate(QStyledItemDelegate):
    """Desenha uma mini barra de progresso com texto 'x/y' (concluídas/total de subtarefas)."""

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        text = index.data(Qt.DisplayRole) or ""
        if not text or "/" not in text:
            painter.restore()
            return

        try:
            done_str, total_str = text.split("/")
            done = int(done_str)
            total = int(total_str)
        except (ValueError, TypeError):
            painter.restore()
            return

        if total <= 0:
            painter.restore()
            return

        fraction = max(0.0, min(1.0, done / total))
        color = get_status_color("Concluído") if fraction >= 1.0 else "#4a6fe3"

        rect = option.rect.adjusted(12, 8, -12, -8)
        if rect.width() < 20 or rect.height() < 6:
            painter.restore()
            return

        track = QColor("#ffffff")
        track.setAlpha(30)
        painter.setBrush(QBrush(track))
        painter.setPen(QPen(track, 0))
        painter.drawRoundedRect(rect, RADIUS_SM, RADIUS_SM)

        if fraction > 0:
            fill_rect = QRectF(rect)
            fill_rect.setWidth(rect.width() * fraction)
            bar_color = QColor(color)
            painter.setBrush(QBrush(bar_color))
            painter.setPen(QPen(bar_color, 0))
            painter.drawRoundedRect(fill_rect, RADIUS_SM, RADIUS_SM)

        painter.setPen(QColor(TEXT_PRIMARY))
        font = QFont()
        font.setBold(True)
        font.setPointSize(FONT_CAPTION)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, text)

        painter.restore()

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        return QSize(max(base.width() + 30, 70), max(base.height(), 26))
