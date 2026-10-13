from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from gui.theme import (
    TEXT_PRIMARY, RADIUS_SM, FONT_CAPTION,
    SUCCESS_GREEN, ERROR_RED, WARNING_ORANGE, ACCENT_BLUE,
    TEXT_DISABLED, get_status_color, get_energy_color,
    TEXT_SECONDARY, BG_CARD
)

STATUS_LABELS = {
    "Pendente": "Pendente",
    "Em Andamento": "Em andamento",
    "Pausado": "Pausado",
    "Aguardando": "Aguardando",
    "Bloqueado": "Bloqueado",
    "Concluído": "Concluído",
    "Ativo": "Ativo",
    "Em Pausa": "Em pausa",
}

ENERGY_LABELS = {
    "Baixa": "Baixa",
    "Média": "Média",
    "Alta": "Alta",
    "Máxima": "Máxima",
    "Crítica": "Crítica",
    "critical": "Crítica",
    "high": "Alta",
    "medium": "Média",
    "low": "Baixa",
}


class Badge(QLabel):
    """Chip de status/prioridade/saude.

    Dois estilos:
      * tinted (padrao) -- fundo e borda na cor com alpha baixa, texto na
        cor cheia. Serve para a maioria dos casos.
      * solid=True -- fundo na cor cheia e texto branco. Usar quando o
        chip precisa se destacar do card (ex.: prioridade de alarme).

    O visual NAO vem do GLOBAL_STYLE porque a cor e dinamica por instancia
    (vem do status/prioridade da entidade). Para cores fixas, prefira uma
    variante no tema.
    """

    def __init__(self, text="", color=ACCENT_BLUE, parent=None, solid=False):
        super().__init__(text, parent)
        self._badge_color = color
        self._solid = solid
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(22)
        self._update_style()

    def _update_style(self):
        if self._solid:
            bg, text_c, border = self._badge_color, "#ffffff", "none"
        else:
            bg = f"{self._badge_color}33"
            text_c = self._badge_color
            border = f"1px solid {self._badge_color}44"
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {text_c};
                border: {border};
                border-radius: {RADIUS_SM - 1}px;
                padding: 1px 8px;
                font-size: {FONT_CAPTION}px;
                font-weight: bold;
            }}
        """)

    def set_color(self, color: str):
        self._badge_color = color
        self._update_style()


def status_badge(status: str) -> Badge:
    color = get_status_color(status)
    label = STATUS_LABELS.get(status, status)
    return Badge(label, color)


def priority_badge(priority: str) -> Badge:
    color = get_energy_color(priority)
    label = ENERGY_LABELS.get(priority, priority)
    return Badge(label, color)


def health_badge(health: str) -> Badge:
    colors = {"Verde": SUCCESS_GREEN, "Amarelo": WARNING_ORANGE, "Vermelho": ERROR_RED}
    color = colors.get(health, TEXT_SECONDARY)
    return Badge(health, color)


def category_badge(category: str) -> Badge:
    return Badge(category, ACCENT_BLUE)
