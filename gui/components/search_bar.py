"""Campo de filtro/busca das listagens.

Usa a variante `QLineEdit#searchBar` do GLOBAL_STYLE -- nao aplique
setStyleSheet aqui. A unica coisa que o componente acrescenta e o
comportamento: largura maxima e botao de limpar.
"""

from PySide6.QtWidgets import QLineEdit


class SearchBar(QLineEdit):
    """Filtro de listagem. `max_width` evita que ele estique e empurre
    os botoes de acao para fora da janela estreita."""

    def __init__(self, placeholder="", max_width=260, parent=None):
        super().__init__(parent)
        self.setObjectName("searchBar")
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setMaximumWidth(max_width)