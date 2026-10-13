"""Botoes da UI.

REGRA: estas classes definem APENAS o objectName. Todo o visual vem do
GLOBAL_STYLE em gui/theme.py. Nao aplique setStyleSheet aqui.

Motivo: stylesheet local tem precedencia sobre o do QApplication e
anula a regra do tema. Foi exatamente isso que gerou a divergencia
anterior -- buttons.py usava `padding: 8px 20px` sem :pressed, o
GLOBAL_STYLE usava `padding: 6px 14px` com :pressed, e as 45 telas que
usavam setObjectName("secondary") ficavam diferentes do componente.

Se precisar de um visual novo, acrescente uma variante `#nome` no
GLOBAL_STYLE e uma classe aqui. Nunca inline.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QToolButton


class _VariantButton(QPushButton):
    """Fabrica de botao por objectName. Sem estilo proprio."""

    OBJECT_NAME = ""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        if self.OBJECT_NAME:
            self.setObjectName(self.OBJECT_NAME)


class PrimaryButton(_VariantButton):
    """Acao principal do contexto. Um por tela."""

    OBJECT_NAME = "primary"


class SecondaryButton(_VariantButton):
    """Acao secundaria (cancelar, voltar, alternativa)."""

    OBJECT_NAME = "secondary"


class DangerButton(_VariantButton):
    """Acao destrutiva (excluir). Vermelho."""

    OBJECT_NAME = "danger"


class SuccessButton(_VariantButton):
    """Confirmacao positiva. Verde."""

    OBJECT_NAME = "success"


class TextButton(_VariantButton):
    """Link / acao inline. Azul, sem fundo nem borda."""

    OBJECT_NAME = "text"


class GhostButton(_VariantButton):
    """Sem crom ate o hover. Usado em toolbars densas."""

    OBJECT_NAME = "ghost"


class IconButton(QToolButton):
    """Botao quadrado de icone (historico, fechar, expandir)."""

    OBJECT_NAME = "icon"

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setObjectName(self.OBJECT_NAME)
        if text:
            self.setText(text)
        self.setCursor(Qt.PointingHandCursor)


class ToggleButton(_VariantButton):
    """Liga/desliga.

    Segue o padrao do AGENTS.md:
      LIGADO    -> fundo preenchido colorido + texto branco
      DESLIGADO -> transparente + borda #555 + texto #aaa
    O rotulo ganha o sufixo ON/OFF e muda junto com o estado.

    Dois modos de estilo:
      * on_name + off_name diferentes (ex.: "success" -> "secondary"):
        troca o objectName conforme o estado.
      * apenas on_name (ex.: "toggleGreen"): o objectName fica fixo e o
        proprio QSS diferencia via :checked / :!checked. E o modo
        preferido para as variantes #toggle* do GLOBAL_STYLE.
    """

    def __init__(self, text="", parent=None, on_label=None, off_label=None,
                 checked=False, on_name="success", off_name="secondary"):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.on_name = on_name
        self.off_name = off_name
        self._on_label = on_label or f"{text}: ON"
        self._off_label = off_label or f"{text}: OFF"
        self.setChecked(checked)
        self._apply_state()
        self.toggled.connect(self._apply_state)

    def _apply_state(self):
        self.setText(self._on_label if self.isChecked() else self._off_label)
        name = self.on_name if self.isChecked() else (self.off_name or self.on_name)
        if self.objectName() != name:
            self.setObjectName(name)
            # Qt casa o stylesheet pelo objectName e cacheia o resultado:
            # sem re-polish a variante nova nao se aplica.
            style = self.style()
            style.unpolish(self)
            style.polish(self)

    def label(self):
        """Rotulo sem o sufixo ON/OFF."""
        return self._off_label.rsplit(": ", 1)[0]