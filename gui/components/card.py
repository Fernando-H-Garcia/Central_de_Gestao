"""Card base.

O visual vem do `QFrame#card` do GLOBAL_STYLE (gui/theme.py). Nao
aplique setStyleSheet aqui -- stylesheet local anula o do tema.

Variantes: se precisar de um card com acento/elevacao/compacto, acrescente
`QFrame#card_nome` no GLOBAL_STYLE e um `objectName` aqui, em vez de
inventar um estilo inline.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout


class Card(QFrame):
    def __init__(self, parent=None, margins=(16, 16, 16, 16), spacing=12):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)

    def layout(self):
        return self._layout