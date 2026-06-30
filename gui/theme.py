# gui/theme.py
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QBrush, QPixmap, QIcon, QPainter, QTextCharFormat, QFont
from PySide6.QtWidgets import QCalendarWidget

# ═══════════════════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ═══════════════════════════════════════════════════════════════════════

# ── Colors ───────────────────────────────────────────────────────────
BG_PRIMARY = "#0b0b14"
BG_SECONDARY = "#13131f"
BG_CARD = "#1c1c2e"
BG_HOVER = "#2d2d55"
BG_INPUT = "#1c1c2e"

TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#888888"
TEXT_BODY = "#e0e0e0"
TEXT_DISABLED = "#666666"

ACCENT_BLUE = "#4a6fe3"
ACCENT_HOVER = "#385bbb"
ACCENT_ACTIVE = "#6384f5"

SUCCESS_GREEN = "#2b8c52"
SUCCESS_HOVER = "#3bbf6e"
ERROR_RED = "#e53935"
ERROR_HOVER = "#f55a56"
WARNING_ORANGE = "#e3a84a"
INFO_CYAN = "#26c6da"

BORDER_SUBTLE = "#2a2a3f"
BORDER_FOCUS = "#4a6fe3"

THEME_PURPLE = "#1e1e3a"

# ── Spacing (px) ────────────────────────────────────────────────────
XS = 4
SM = 8
MD = 16
LG = 24
XL = 32

# ── Border Radius (px) ──────────────────────────────────────────────
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 10

# ── Typography (px) ─────────────────────────────────────────────────
FONT_CAPTION = 11
FONT_BODY = 12
FONT_BODY_LG = 14
FONT_SUBTITLE = 17
FONT_TITLE = 22
FONT_HEADER = 28

# ── Shadows (QSS drop-shadow) ───────────────────────────────────────
SHADOW_CARD = "drop-shadow(0 2px 4px rgba(0,0,0,0.3))"
SHADOW_POPUP = "drop-shadow(0 8px 16px rgba(0,0,0,0.5))"


# ═══════════════════════════════════════════════════════════════════════
# STYLESHEET BUILDER
# ═══════════════════════════════════════════════════════════════════════

def _qss(*rules: str) -> str:
    return "; ".join(rules) + ";"

def bg_card() -> str:
    return f"background-color: {BG_CARD}"

def text_primary() -> str:
    return f"color: {TEXT_PRIMARY}"

def border_radius(r: int) -> str:
    return f"border-radius: {r}px"

def border_subtle() -> str:
    return f"border: 1px solid {BORDER_SUBTLE}"

def border_focus() -> str:
    return f"border: 1px solid {BORDER_FOCUS}"

def padding_all(p: int) -> str:
    return f"padding: {p}px"

def padding_hv(h: int, v: int) -> str:
    return f"padding: {v}px {h}px"


GLOBAL_STYLE = f"""
QWidget {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', Arial, sans-serif;
}}

QDialog {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
}}

QFrame#panel, QScrollArea, QStackedWidget {{
    background-color: transparent;
    border: none;
}}

QFrame#card {{
    background-color: {BG_CARD};
    border-radius: {RADIUS_LG}px;
}}

QFrame#Sidebar {{
    background-color: {BG_CARD};
    border-right: 1px solid {BORDER_SUBTLE};
    margin: 0px;
    padding: 0px;
}}

QFrame#Sidebar QPushButton {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    text-align: left;
    padding: 10px 15px;
    border: none;
    font-size: {FONT_BODY_LG}px;
    margin-bottom: 5px;
}}
QFrame#Sidebar QPushButton:hover {{
    background-color: {BORDER_SUBTLE};
    border-radius: {RADIUS_SM}px;
}}
QFrame#Sidebar QPushButton:pressed {{
    background-color: {BG_HOVER};
    border-radius: {RADIUS_SM}px;
}}
QFrame#Sidebar QPushButton:checked {{
    background-color: {BG_HOVER};
    border-left: 3px solid {ACCENT_BLUE};
    border-radius: 0;
    border-top-right-radius: {RADIUS_SM}px;
    border-bottom-right-radius: {RADIUS_SM}px;
    font-weight: bold;
}}

QLabel {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
}}
QLabel#header {{
    font-size: {FONT_HEADER}px;
    font-weight: bold;
}}
QLabel#subtitle {{
    color: {TEXT_SECONDARY};
}}

QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    {padding_hv(15, 8)};
    {border_radius(RADIUS_SM)};
    {border_subtle()};
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
    border: 1px solid {BORDER_FOCUS};
}}
QPushButton:pressed {{
    background-color: {BG_CARD};
}}
QPushButton#primary {{
    background-color: {ACCENT_BLUE};
    border: none;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT_ACTIVE};
}}
QPushButton#primary:pressed {{
    background-color: {ACCENT_ACTIVE};
}}
QPushButton#success {{
    background-color: {SUCCESS_GREEN};
    border: none;
}}
QPushButton#success:hover {{
    background-color: {SUCCESS_HOVER};
}}
QPushButton#success:pressed {{
    background-color: {SUCCESS_HOVER};
}}
QPushButton#danger {{
    background-color: {ERROR_RED};
    border: none;
}}
QPushButton#danger:hover {{
    background-color: {ERROR_HOVER};
}}
QPushButton#danger:pressed {{
    background-color: {ERROR_HOVER};
}}
QPushButton#secondary {{
    background-color: transparent;
    border: 1px solid #555555;
    color: #aaaaaa;
    padding: 6px 14px;
    border-radius: 5px;
    font-weight: bold;
}}
QPushButton#secondary:hover {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
    {border_focus()};
}}
QPushButton#secondary:pressed {{
    background-color: {BORDER_SUBTLE};
    color: {TEXT_PRIMARY};
    {border_focus()};
}}

QLineEdit, QTextEdit, QDateEdit, QTimeEdit {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    {border_subtle()};
    {border_radius(RADIUS_SM)};
    {padding_all(5)};
}}
QComboBox {{
    background-color: {BG_INPUT};
    color: {TEXT_PRIMARY};
    {border_subtle()};
    {border_radius(RADIUS_SM)};
    {padding_all(5)};
    padding-right: 20px;
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {{
    {border_focus()};
}}
QComboBox::drop-down {{
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    selection-background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}

QTableWidget, QTreeWidget, QListWidget {{
    background-color: {BG_CARD};
    alternate-background-color: #1a1a2e;
    color: {TEXT_PRIMARY};
    border: none;
    gridline-color: {BORDER_SUBTLE};
    outline: none;
    selection-background-color: {BG_HOVER};
    selection-color: {TEXT_PRIMARY};
}}
QTableWidget::item, QTreeWidget::item, QListWidget::item {{
    padding: 8px 10px;
    border: none;
}}
QTableWidget::item:hover, QTreeWidget::item:hover, QListWidget::item:hover {{
    background-color: #252540;
}}
QTableWidget::item:selected, QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {BG_HOVER};
    color: {TEXT_PRIMARY};
}}
QTableWidget::item:selected:hover, QTreeWidget::item:selected:hover, QListWidget::item:selected:hover {{
    background-color: {ACCENT_HOVER};
}}
QHeaderView::section {{
    background-color: {BG_SECONDARY};
    color: {TEXT_SECONDARY};
    font-weight: bold;
    border: none;
    border-right: 1px solid {BORDER_SUBTLE};
    padding: 8px 12px;
}}

QScrollBar:vertical {{
    background: {BG_SECONDARY};
    width: 12px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_SUBTLE};
    min-height: 20px;
    {border_radius(RADIUS_SM + 2)};
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT_BLUE};
}}

QTabWidget::pane {{
    {border_subtle()};
}}
QTabBar::tab {{
    background: {BG_CARD};
    color: {TEXT_SECONDARY};
    {padding_hv(20, 10)};
    {border_subtle()};
    border-bottom: none;
    {border_radius(RADIUS_SM)};
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
}}
QTabBar::tab:selected {{
    background: {BORDER_SUBTLE};
    color: {TEXT_PRIMARY};
    font-weight: bold;
}}

QMenu {{
    background-color: {BG_CARD};
    color: white;
    {border_subtle()};
}}
QMenu::item {{
    {padding_hv(25, 5)};
}}
QMenu::item:selected {{
    background-color: {BG_HOVER};
}}

QCalendarWidget {{
    background-color: {BG_CARD};
}}
QCalendarWidget QToolButton {{
    color: {TEXT_PRIMARY};
    background-color: {BORDER_SUBTLE};
    {border_subtle()};
    {border_radius(RADIUS_SM)};
    {padding_hv(8, 4)};
    font-weight: bold;
}}
QCalendarWidget QToolButton:hover {{
    background-color: #3a3a5f;
}}
QCalendarWidget QAbstractItemView {{
    background-color: {BG_CARD};
    color: {TEXT_BODY};
    selection-background-color: {ACCENT_BLUE};
    selection-color: {TEXT_PRIMARY};
    outline: none;
}}

QMessageBox {{
    background-color: {BG_CARD};
}}

QToolTip {{
    background-color: {THEME_PURPLE};
    color: {TEXT_PRIMARY};
    {border_subtle()};
    {border_radius(RADIUS_SM)};
    {padding_hv(8, 4)};
    font-size: {FONT_CAPTION}px;
}}
"""


# ═══════════════════════════════════════════════════════════════════════
# COLOR MAPS & HELPERS
# ═══════════════════════════════════════════════════════════════════════

STATUS_COLORS = {
    "Pendente": TEXT_SECONDARY,
    "Em Andamento": WARNING_ORANGE,
    "Pausado": TEXT_DISABLED,
    "Aguardando": "#d66b27",
    "Bloqueado": ERROR_RED,
    "Concluído": SUCCESS_GREEN,
    "Ativo": ACCENT_BLUE,
    "Em Pausa": WARNING_ORANGE,
}

ENERGY_COLORS = {
    "Baixa": ACCENT_BLUE,
    "Média": SUCCESS_GREEN,
    "Alta": WARNING_ORANGE,
    "Máxima": ERROR_RED,
    "Crítica": ERROR_RED,
}


def get_status_color(status: str) -> str:
    return STATUS_COLORS.get(status, TEXT_PRIMARY)


def get_energy_color(energy: str) -> str:
    return ENERGY_COLORS.get(energy, TEXT_PRIMARY)


def create_color_icon(color_hex: str) -> QIcon:
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(2, 2, 12, 12)
    painter.end()
    return QIcon(pixmap)


def set_combobox_colors(combo, color_map):
    for i in range(combo.count()):
        text = combo.itemText(i)
        if text in color_map:
            combo.setItemData(i, QBrush(QColor(color_map[text])), Qt.ForegroundRole)


def apply_combobox_dynamic_color(combo, color_func):
    def update_style(text):
        color = color_func(text)
        style = f"""
        QComboBox {{
            background-color: {BG_INPUT};
            color: {color};
            font-weight: bold;
            {border_subtle()}
            {border_radius(RADIUS_SM)}
            {padding_all(5)}
            padding-right: 20px;
        }}
        QComboBox:focus {{
            {border_focus()}
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        """
        combo.setStyleSheet(style)
    combo.currentTextChanged.connect(update_style)
    update_style(combo.currentText())


def format_colored_label(prefix: str, value: str, color_func) -> str:
    color = color_func(value)
    return f'{prefix} <span style="color: {color}; font-weight: bold;">{value}</span>'


# ═══════════════════════════════════════════════════════════════════════
# CALENDAR HELPERS
# ═══════════════════════════════════════════════════════════════════════

def style_calendar_today(date_edit):
    cal = date_edit.calendarWidget()
    if not cal:
        cal = date_edit.findChild(QCalendarWidget)
    if not cal:
        return
    today_fmt = QTextCharFormat()
    today_fmt.setBackground(QColor(ACCENT_BLUE))
    today_fmt.setForeground(QColor(TEXT_PRIMARY))
    today_fmt.setFontWeight(QFont.Bold)
    cal.setDateTextFormat(QDate.currentDate(), today_fmt)

    def on_page_changed(year, month):
        cal.setDateTextFormat(QDate.currentDate(), today_fmt)
    cal.currentPageChanged.connect(on_page_changed)
