from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class CollapsibleSection(QWidget):
    """Seção com cabeçalho clicável que recolhe/expande o corpo.

    `depth`: nível de aninhamento (0 = nível raiz). Cada nível extra indenta o
    corpo e adiciona uma borda-guia vertical à esquerda, deixando claro que o
    conteúdo está contido dentro do bloco de um nível superior.
    """

    def __init__(self, title="", parent=None, default_collapsed=False, accent="#e67e22", depth=0, bg=None):
        super().__init__(parent)
        self._collapsed = bool(default_collapsed)
        self._title = title
        self._accent = accent
        self._depth = max(0, int(depth))
        self._bg = bg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QPushButton()
        self.header.setCursor(Qt.PointingHandCursor)
        self.header.setCheckable(False)
        self.header.setFlat(True)
        self.header.setStyleSheet(self._header_css())
        font = QFont()
        font.setBold(True)
        self.header.setFont(font)
        self.header.clicked.connect(self.toggle)
        layout.addWidget(self.header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        indent = 8 + self._depth * 18
        self.body_layout.setContentsMargins(indent, 4, 0, 6)
        self.body_layout.setSpacing(4)
        layout.addWidget(self.body)

        self._update_header()

    def _header_colors(self):
        # Cor do cabeçalho varia por nível para facilitar a leitura da cascata.
        if self._bg is not None:
            return self._bg
        if self._depth == 0:
            bg = f"rgba({self._rgb()}, 0.10)"
        elif self._depth == 1:
            bg = f"rgba({self._rgb()}, 0.07)"
        elif self._depth == 2:
            bg = f"rgba({self._rgb()}, 0.05)"
        else:
            bg = f"rgba({self._rgb()}, 0.04)"
        return bg

    def _hover_color(self):
        # Hover: se tem fundo fixo, clareia um pouco; senão usa a transparência do accent.
        if self._bg is not None:
            return f"rgba({self._rgb_bg()}, 0.30)"
        return f"rgba({self._rgb()}, 0.16)"

    def _pressed_color(self):
        if self._bg is not None:
            return f"rgba({self._rgb_bg()}, 0.40)"
        return f"rgba({self._rgb()}, 0.22)"

    def _header_css(self):
        bg = self._header_colors()
        # A borda-guia vertical (esquerda) escala com a profundidade.
        lw = 2 + int(self._depth * 2)
        return f"""
            QPushButton {{
                background: {bg};
                color: {self._accent};
                border-left: {lw}px solid {self._accent};
                border-radius: 6px;
                padding: 6px 10px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {self._hover_color()};
            }}
            QPushButton:pressed {{
                background: {self._pressed_color()};
            }}
        """

    def _rgb(self):
        hexv = self._accent.lstrip("#")
        try:
            r = int(hexv[0:2], 16)
            g = int(hexv[2:4], 16)
            b = int(hexv[4:6], 16)
            return f"{r}, {g}, {b}"
        except Exception:
            return "230, 126, 34"

    def _rgb_bg(self):
        hexv = self._bg.lstrip("#")
        try:
            r = int(hexv[0:2], 16)
            g = int(hexv[2:4], 16)
            b = int(hexv[4:6], 16)
            return f"{r}, {g}, {b}"
        except Exception:
            return "33, 26, 20"

    def set_depth(self, depth):
        self._depth = max(0, int(depth))
        indent = 8 + self._depth * 18
        self.body_layout.setContentsMargins(indent, 4, 0, 6)
        self.header.setStyleSheet(self._header_css())

    def set_title(self, title):
        self._title = title
        self._update_header()

    def _update_header(self):
        arrow = "▼" if not self._collapsed else "▶"
        prefix = ""
        if self._depth == 1:
            prefix = "└─ "
        elif self._depth > 1:
            prefix = ("  " * (self._depth - 1)) + "└─ "
        self.header.setText(f"{arrow}  {prefix}{self._title}")
        self.body.setVisible(not self._collapsed)

    def toggle(self):
        self._collapsed = not self._collapsed
        self._update_header()

    def set_collapsed(self, collapsed):
        self._collapsed = bool(collapsed)
        self._update_header()