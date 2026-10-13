from PySide6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QLabel,
                               QWidget, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from gui.theme import TEXT_SECONDARY, FONT_BODY_LG


class _Spacing(QWidget):
    """Espacador fixo. Substitui addSpacing(), que nao sobrevive a um
    layout reordenado."""

    def __init__(self, width):
        super().__init__()
        self.setFixedWidth(width)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)


class ElidedTitle(QLabel):
    """Titulo do cabecalho que nunca some.

    Sem isto, um titulo longo era espremido pelo painel de Referencias e
    pelos botoes: o QLabel recebia 102px para um texto de 2212px e
    simplesmente nao desenhava nada. Aqui o texto e truncado com reticencias
    conforme o espaco real, e o tooltip traz o texto completo.
    """

    def __init__(self, text="", min_width=200, parent=None):
        super().__init__(parent)
        self._full_text = text or ""
        self._min_width = min_width
        # Ignored: o rotulo NAO exige espaco -- ele cede e trunca.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(min_width)
        self._refresh()

    def full_text(self):
        """Texto completo, independente do espaco disponivel."""
        return self._full_text

    def setText(self, text):
        self._full_text = text or ""
        self._refresh()

    def text(self):
        """Texto EXIBIDO (ja trunhado), como manda o QLabel.

        Nao devolve o texto completo: quem precisar dele usa
        full_text(). Devolver o completo aqui quebraria o contrato do
        QLabel e enganaria quem mede o que o usuario ve.
        """
        return super().text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        fm = QFontMetrics(self.font())
        disponivel = max(0, self.width() - 2)
        super().setText(
            fm.elidedText(self._full_text, Qt.ElideRight, disponivel)
        )
        self.setToolTip(self._full_text)


class PageHeader(QFrame):
    """Cabecalho de pagina: [widgets esquerda] [titulo] [painel] [BOTOES].
    
        Regra de layout que este componente garante:
          - o titulo e o unico elemento que PODE crescer e encolher;
          - botoes e paineis tem tamanho FIXO, entao nunca empurram o titulo
            para fora nem saem do centro da tela;
          - os botoes ficam SEMPRE no extremo direito, depois dos paineis.
    """

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

        self.title_label = ElidedTitle(title)
        self.title_label.setObjectName("header")
        text_area.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: {FONT_BODY_LG}px; padding: 0; border: none;"
        )
        self.subtitle_label.setVisible(bool(subtitle))
        self.subtitle_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.subtitle_label.setMinimumWidth(200)
        text_area.addWidget(self.subtitle_label)

        self._left_layout.addLayout(text_area, stretch=1)

        # Ordem deliberada: titulo | paineis | BOTOES no extremo direito.
        # Antes os botoes vinham antes dos paineis, entao com o painel de
        # Referencias (largo) o botao de acao acabava no meio da tela.
        self._right_layout = QHBoxLayout()
        self._right_layout.setSpacing(12)
        layout.addLayout(self._right_layout)

        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(8)
        layout.addLayout(self._button_layout)
        self._button_layout.addStretch()

    def set_title(self, title: str):
        self.title_label.setText(title)

    def set_subtitle(self, subtitle: str):
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def add_left_widget(self, widget):
        self._left_layout.insertWidget(0, widget)

    def add_button(self, button):
        # Botao nunca cresce nem encolhe horizontalmente: sem isso ele
        # disputa espaco com o titulo e empurra o cabecalho pro centro.
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self._button_layout.addWidget(button)

    def add_right_widget(self, widget, spacing=12):
        """Painel entre o titulo e os botoes (ex.: painel de referencias).

        Tambem recebe tamanho fixo pelo mesmo motivo dos botoes.
        """
        widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self._right_layout.addWidget(widget)
        if spacing:
            self._right_layout.addWidget(_Spacing(spacing))
