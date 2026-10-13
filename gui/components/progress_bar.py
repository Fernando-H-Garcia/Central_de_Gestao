"""Barra de progresso.

REGRA DE COR: a cor NAO e derivada da porcentagem.

A versao anterior fazia vermelho abaixo de 40%, o que e semanticamente
errado neste app: um projeto em 10% e normal, e vermelho aqui significa
"atrasado" (mesma convencao do Gantt em gantt_tree_qt.bar_color).

A cor e sempre ACCENT_BLUE por padrao -- azul e "progresso", nao "ruim".
Quem sabe o estado semantico (concluido / atrasado / vencendo) informa
via set_color(), usando os mesmos tokens do Gantt.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QFontMetrics
from gui.theme import (
    BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY, ACCENT_BLUE,
    RADIUS_SM, FONT_BODY, FONT_CAPTION
)


class ProgressBar(QWidget):
    """Barra de progresso com cor semantica explicita.

    Args:
        value/maximum: numeros (maximum nunca fica abaixo de 1).
        text: rotulo desenhado DENTRO da barra, centralizado. Vazio = sem
              texto. Mantem o visual do QProgressBar que substitui.
        color: cor do preenchimento. None = ACCENT_BLUE (neutro).
    """

    def __init__(self, value=0, maximum=100, parent=None, text="", color=None):
        super().__init__(parent)
        self._value = value
        self._maximum = max(1, maximum)
        self._text = text
        self._color = color or ACCENT_BLUE
        self.setFixedHeight(20)
        self.setMinimumWidth(100)

    # -- estado ------------------------------------------------------------
    def set_value(self, value: int):
        self._value = max(0, min(value, self._maximum))
        self.update()

    def set_maximum(self, maximum: int):
        self._maximum = max(1, maximum)
        self._value = max(0, min(self._value, self._maximum))
        self.update()

    def set_text(self, text: str):
        self._text = text or ""
        self.updateGeometry()
        self.update()

    def set_color(self, color: str):
        """Cor semantica do preenchimento. None volta ao azul neutro."""
        self._color = color or ACCENT_BLUE
        self.update()

    def value(self) -> int:
        return self._value

    def percentage(self) -> float:
        return (self._value / self._maximum) * 100

    # -- pintura -----------------------------------------------------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(BG_CARD))
        painter.drawRoundedRect(0, 0, w, h, RADIUS_SM, RADIUS_SM)

        pct = self.percentage()
        fill_w = int(w * (pct / 100))
        if fill_w > 0:
            painter.setBrush(QColor(self._color))
            painter.drawRoundedRect(0, 0, fill_w, h, RADIUS_SM, RADIUS_SM)

        if self._text:
            painter.setPen(QColor(TEXT_PRIMARY))
            fm = QFontMetrics(self.font())
            needed = fm.horizontalAdvance(self._text) + 8
            # centra no trecho preenchido; se nao couber, centra na barra toda
            if needed <= fill_w:
                rect = QRect(0, 0, fill_w, h)
            else:
                rect = QRect(0, 0, w, h)
            painter.drawText(rect, Qt.AlignCenter, self._text)

        painter.end()

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(120, 20)


class ProgressBarWithLabel(ProgressBar):
    """Mesma barra, com a porcentagem a direita em vez de dentro.

    Use quando o texto dentro da barra nao caiba -- a barra costuma ser
    estreita em tabela/card.
    """

    def __init__(self, value=0, maximum=100, parent=None, color=None):
        super().__init__(value, maximum, parent, text="", color=color)
        self._inner = ProgressBar(value, maximum, None, text="", color=color)
        self._pct_label = QLabel(f"{self.percentage():.0f}%")
        self._pct_label.setFixedWidth(36)
        self._pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._pct_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: {FONT_CAPTION}px; font-weight: bold; background: transparent; border: none;"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(self._inner, stretch=1)
        lay.addWidget(self._pct_label)

    def set_value(self, value: int):
        super().set_value(value)
        self._inner.set_value(value)
        self._pct_label.setText(f"{self._inner.percentage():.0f}%")

    def set_color(self, color: str):
        super().set_color(color)
        self._inner.set_color(color)