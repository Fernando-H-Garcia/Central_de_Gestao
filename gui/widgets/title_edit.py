from PySide6.QtWidgets import QTextEdit
from gui.theme import autogrow_text_edit


class TitleEdit(QTextEdit):
    """Campo de título com quebra de linha e altura dinâmica (cresce com o texto)."""

    def __init__(self, parent=None, placeholder=""):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setAcceptRichText(False)
        autogrow_text_edit(self, min_h=34, max_h=300)

    def text(self):
        return self.toPlainText()

    def setText(self, text):
        self.setPlainText(text or "")
