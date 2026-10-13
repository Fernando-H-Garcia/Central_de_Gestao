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

    Dois modos:
      wrap=True (padrao) -- quebra em varias linhas, como o titulo fazia
        antes. Preferido: mostra mais informacao sem cortar nada.
      wrap=False -- trunca numa linha com reticencias.

    Nos dois modos o texto completo fica no tooltip, e nenhum dos dois
    deixa o rotulo com 0px de largura -- era o que acontecia: o QLabel
    perdia a disputa por espaco e simplesmente nao desenhava nada.
    """

    def __init__(self, text="", min_width=200, wrap=True, max_lines=2, parent=None):
        super().__init__(parent)
        self._full_text = text or ""
        self._min_width = min_width
        self._wrap = wrap
        self._max_lines = max_lines
        self.setWordWrap(False)  # a quebra e feita em _wrap_text
        if wrap:
            # Expanding (horizontal) + Preferred (vertical).
            #
            # Expanding: o rotulo ocupa TODO o espaco que sobrar, e o que
            # faz o bloco da direita encostar na borda.
            #
            # Preferred e NAO Minimum na vertical: com wordWrap o
            # sizeHint do QLabel depende da largura atual, e Minimum
            # proibe encolher depois -- a altura ficava presa no valor
            # calculado com a largura estreita (508px num titulo que
            # cabia em 5 linhas).
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        else:
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
        """Texto EXIBIDO, como manda o QLabel.

        No modo wrap devolve o texto com quebras de linha; no modo elide,
        o texto truncado. Quem precisar do original usa full_text().
        """
        return super().text()

    def set_wrap(self, wrap):
        self._wrap = wrap
        self.setWordWrap(wrap)
        self.setSizePolicy(QSizePolicy.Expanding if wrap else QSizePolicy.Ignored,
                          QSizePolicy.Preferred)
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _wrap_text(self, fm, largura):
        """Quebra o texto em no maximo `max_lines` linhas que cabem em
        `largura`. A ultima linha recebe reticencias.

        Feito a mao, e nao com QLabel.wordWrap, porque o wordWrap do Qt
        depende de heightForWidth/sizeHint e o layout acabava usando uma
        altura calculada com a largura errada.

        O limite de linhas e essencial: a fonte do cabecalho e grande
        (28px) e um titulo de entidade longo exigiria dezenas de linhas,
        empurrando todo o conteudo para fora da tela.
        """
        palavras = self._full_text.split()
        if not palavras:
            return [""]
        linhas, atual = [], palavras[0]
        for p in palavras[1:]:
            tentativa = f"{atual} {p}"
            if fm.horizontalAdvance(tentativa) <= largura:
                atual = tentativa
            else:
                linhas.append(atual)
                atual = p
                if len(linhas) == self._max_lines:
                    break
        restou = palavras[1 + sum(len(l.split()) for l in linhas):]
        if self._max_lines and len(linhas) == self._max_lines and restou:
            # ainda ha texto: marca com reticencias
            while linhas and fm.horizontalAdvance(linhas[-1] + "…") > largura:
                linhas[-1] = linhas[-1].rsplit(" ", 1)[0]
                restou = palavras[1 + sum(len(l.split()) for l in linhas):]
            linhas[-1] = linhas[-1] + "…"
        else:
            linhas.append(atual)
        return linhas

    def _refresh(self):
        self.setToolTip(self._full_text)

        if not self._wrap:
            self._clear_fixed_height()
            fm = QFontMetrics(self.font())
            truncado = fm.elidedText(self._full_text, Qt.ElideRight,
                                     max(0, self.width() - 2))
            if super().text() != truncado:
                super().setText(truncado)
            return

        self.setWordWrap(False)
        fm = QFontMetrics(self.font())
        largura = max(20, self.width() - 2)
        linhas = self._wrap_text(fm, largura)
        texto = "\n".join(linhas)
        if super().text() != texto:
            super().setText(texto)

        alvo = len(linhas) * fm.height() + 4
        if abs(self.height() - alvo) > 1:
            self.setFixedHeight(alvo)

    def _clear_fixed_height(self):
        if self.minimumHeight() != 0 or self.maximumHeight() != 16777215:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)


class PageHeader(QFrame):
    """Cabecalho de pagina: [widgets esquerda] [titulo] [painel] [BOTOES].
    
        Regra de layout que este componente garante:
          - o titulo e o unico elemento que PODE crescer e encolher;
          - botoes e paineis tem tamanho FIXO, entao nunca empurram o titulo
            para fora nem saem do centro da tela;
          - os botoes ficam SEMPRE no extremo direito, depois dos paineis.
    """

    def __init__(self, title="", subtitle="", parent=None, wrap_title=True):
        super().__init__(parent)
        self.setObjectName("pageHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self._left_layout = QHBoxLayout()
        self._left_layout.setSpacing(8)

        text_area = QVBoxLayout()
        text_area.setSpacing(2)

        self.title_label = ElidedTitle(title, wrap=wrap_title)
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

        # O stretch=1 do titulo precisa estar NO LAYOUT EXTERNO. Sem ele
        # nenhum item externo tem fator de crescimento, o espaco extra ia
        # para o addStretch() do fim e os paineis/botoes acabavam no meio
        # da tela.
        layout.addLayout(self._left_layout, 1)

        # Ordem deliberada: titulo | paineis | BOTOES no extremo direito.
        self._right_layout = QHBoxLayout()
        self._right_layout.setSpacing(12)
        layout.addLayout(self._right_layout)

        # Sem addStretch() aqui: quem empurra para a direita e o titulo,
        # acima. Um stretch no fim puxaria os botoes de volta ao centro.
        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(8)
        layout.addLayout(self._button_layout)

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
