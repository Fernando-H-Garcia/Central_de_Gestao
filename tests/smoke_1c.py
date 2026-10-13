import os
import re
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication, QMenu, QTabWidget, QFrame

app = QApplication(sys.argv)

from gui.theme import GLOBAL_STYLE

app.setStyleSheet(GLOBAL_STYLE)

ok, fail = [], []


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


def t_qmenu():
    """Nenhum QMenu pode mais ter stylesheet proprio."""
    offenders = []
    for path in __import__("pathlib").Path("gui").rglob("*.py"):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"(menu|_menu)\.setStyleSheet", line):
                offenders.append(f"{path}:{i}")
    assert not offenders, "QMenu com stylesheet inline: " + "; ".join(offenders)


check("QMenu: nenhuma stylesheet inline", t_qmenu)


def t_qmenu_theme():
    assert "QMenu::separator" in GLOBAL_STYLE, "tema perdeu o estilo de separador"
    assert "QMenu::item:disabled" in GLOBAL_STYLE, "tema perdeu o estilo de item desabilitado"
    assert "QMenu::item:selected" in GLOBAL_STYLE
    # recorta SO o bloco do QMenu (o proximo seletor e QFrame#autocompletePopup),
    # para nao pegar o popup de autocomplete que usa a mesma cor de selecao.
    ini = GLOBAL_STYLE.index("QMenu {")
    prox = GLOBAL_STYLE.index("QFrame#autocompletePopup")
    bloco = GLOBAL_STYLE[ini:prox]
    # o item selecionado usa BG_HOVER (mesmo hover dos botoes), nao o azul
    # generico ACCENT_BLUE que dois menus da tarefa usavam inline
    sel = bloco[bloco.index("QMenu::item:selected"):]
    sel = sel[:sel.index("}")]
    assert "#4a6fe3" not in sel, "item selecionado do menu voltou ao azul generico"
    assert "#2d2d55" in sel, "item selecionado deveria usar BG_HOVER"
    assert "border-radius" in bloco, "bloco do QMenu sem raio"


check("QMenu: tema completo (raio, padding, separador, disabled)", t_qmenu_theme)


def t_qtabwidget():
    offenders = []
    for path in __import__("pathlib").Path("gui").rglob("*.py"):
        if path.name == "theme.py":  # o proprio GLOBAL_STYLE e a fonte da regra
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "QTabWidget::pane" in line or "QTabBar::tab" in line:
                offenders.append(f"{path}:{i}")
    assert not offenders, "QSS de abas inline ainda existe: " + "; ".join(offenders)
    assert "QTabWidget#nestedTabs" in GLOBAL_STYLE, "tema perdeu a variante de abas aninhadas"


check("QTabWidget: 0 QSS inline + variante nestedTabs no tema", t_qtabwidget)


def t_searchbar():
    from gui.components.search_bar import SearchBar

    sb = SearchBar("Filtrar...", max_width=280)
    assert sb.objectName() == "searchBar"
    assert sb.maximumWidth() == 280
    assert sb.styleSheet() == "", "SearchBar nao deve aplicar stylesheet local"
    assert "QLineEdit#searchBar" in GLOBAL_STYLE
    offenders = [f"{p}" for p in __import__("pathlib").Path("gui").rglob("*.py")
                 if "max-width: 280px" in p.read_text(encoding="utf-8")
                 or "max-width: 250px" in p.read_text(encoding="utf-8")]
    assert not offenders, "searchbar inline ainda em: " + ", ".join(offenders)


check("SearchBar: componente + variante no tema", t_searchbar)


def t_card():
    from gui.components.card import Card

    v = Card()
    assert v.objectName() == "card"
    assert v.layout().count() == 0
    h = Card(orientation="horizontal")
    assert h.layout().spacing() == 12
    from PySide6.QtWidgets import QHBoxLayout
    assert isinstance(h.layout(), QHBoxLayout), "orientation=horizontal deveria dar QHBoxLayout"
    assert isinstance(v.layout(), QVBoxLayoutTypes := __import__("PySide6.QtWidgets", fromlist=["QVBoxLayout"]).QVBoxLayout)


check("Card: orientacao vertical/horizontal", t_card)


def t_views():
    from gui.views.projects_qt import ProjectsQt
    from gui.views.ideas_qt import IdeasQt
    from gui.views.agenda_qt import AgendaQt
    from gui.views.wiki_qt import WikiQt

    pv = ProjectsQt()
    for card in pv.findChildren(QFrame):
        if card.objectName() == "card":
            assert card.styleSheet() == "", "card de projeto ainda tem stylesheet inline"

    av = IdeasQt()
    assert av.search_bar.objectName() == "searchBar"
    assert av.search_bar.maximumWidth() == 250

    ag = AgendaQt()
    assert ag.agenda_tabs.styleSheet() == "", "agenda_tabs ainda tem QSS inline"
    assert ag.project_alarm_tabs.objectName() == "nestedTabs"
    assert ag.project_event_tabs.objectName() == "nestedTabs"
    assert not hasattr(ag, "_nested_tab_style"), "_nested_tab_style deveria ter sumido"

    wv = WikiQt()
    frames = [f for f in wv.findChildren(QFrame) if f.objectName() == "card"]
    assert len(frames) >= 2, f"esperava meta_frame e attach_frame como Card, achei {len(frames)}"
    for f in frames:
        assert f.styleSheet() == "", f"Card {f} ainda tem stylesheet inline"


check("views: ProjectsQt/IdeasQt/AgendaQt/WikiQt migradas", t_views)


def t_backnav():
    from gui.components.back_nav_widget_qt import BackNavWidget

    b = BackNavWidget()
    assert b._menu.styleSheet() == "", "menu de historico ainda tem stylesheet inline"
    assert callable(b._populate_menu)


check("BackNavWidget: menu de historico sem QSS local", t_backnav)


def t_mainwindow():
    from gui.main_window_qt import MainWindow

    w = MainWindow()
    from gui.main_window_qt import NAV_NAMES
    for idx in range(len(NAV_NAMES)):
        w._show_page(idx)
        marked = [i for i, b in w.nav_buttons.items() if b.isChecked()]
        assert marked == [idx]


check("MainWindow: sidebar ok", t_mainwindow)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)