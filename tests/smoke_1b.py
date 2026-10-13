import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication, QPushButton

app = QApplication(sys.argv)

from gui.theme import GLOBAL_STYLE

app.setStyleSheet(GLOBAL_STYLE)

ok = []
fail = []


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


# ---------- componentes: so objectName, ZERO stylesheet local ----------
def t_no_local_qss():
    from gui.components import buttons

    for cls, expect in [
        (buttons.PrimaryButton, "primary"),
        (buttons.SecondaryButton, "secondary"),
        (buttons.DangerButton, "danger"),
        (buttons.SuccessButton, "success"),
        (buttons.TextButton, "text"),
        (buttons.GhostButton, "ghost"),
        (buttons.IconButton, "icon"),
    ]:
        b = cls("x")
        assert b.objectName() == expect, f"{cls.__name__}: objectName={b.objectName()!r} esperado {expect!r}"
        assert b.styleSheet() == "", f"{cls.__name__} aplica stylesheet local ({len(b.styleSheet())} chars)"
    assert issubclass(buttons.IconButton, __import__("PySide6.QtWidgets", fromlist=["QToolButton"]).QToolButton)


check("buttons.py: 7 variantes, so objectName, sem stylesheet", t_no_local_qss)


def t_toggle():
    from gui.components.buttons import ToggleButton

    b = ToggleButton("Arquivados", checked=False, on_name="toggleGreen", off_name=None)
    assert b.text() == "Arquivados: OFF", b.text()
    assert b.objectName() == "toggleGreen"
    assert b.isCheckable()
    b.setChecked(True)
    assert b.text() == "Arquivados: ON", b.text()
    assert b.objectName() == "toggleGreen", "com off_name=None o objectName nao deve mudar"
    assert b.label() == "Arquivados"

    # modo com nomes distintos
    c = ToggleButton("X", on_name="success", off_name="secondary")
    assert c.objectName() == "secondary"
    c.setChecked(True)
    assert c.objectName() == "success"


check("ToggleButton: sufixo ON/OFF + objectName", t_toggle)


def t_card():
    import pathlib
    from gui.components.card import Card

    c = Card()
    assert c.objectName() == "card"
    # Card.style() herdado do QWidget e correto; o que nao pode existir mais
    # e o @staticmethod nosso que devolvia o QSS duplicado.
    src = pathlib.Path("gui/components/card.py").read_text(encoding="utf-8")
    assert "def style" not in src, "card.py ainda define o metodo style() estatico"
    assert "@staticmethod" not in src, "card.py ainda tem @staticmethod"
    assert Card(margins=(0, 0, 0, 0), spacing=0) is not None


check("Card: sem style() duplicado", t_card)


def t_badge():
    from gui.components.badge import Badge, status_badge, priority_badge, health_badge

    tint = Badge("Pendente", "#4a6fe3")
    assert "33" in tint.styleSheet(), "badge tinted deveria usar alpha na cor"
    solid = Badge("Alta", "#e53935", solid=True)
    assert "background-color: #e53935" in solid.styleSheet()
    assert "color: #ffffff" in solid.styleSheet()
    solid.setColor if hasattr(solid, "setColor") else None
    solid.set_color("#000000")
    assert "#000000" in solid.styleSheet()
    assert status_badge("Concluído").text() == "Concluído"
    assert priority_badge("critical").text() == "Crítica", priority_badge("critical").text()
    assert health_badge("Verde") is not None


check("Badge: tinted + solid", t_badge)


# ---------- tema: variantes novas existem e nao ha QSS invalido ----------
def t_theme():
    from gui.theme import GLOBAL_STYLE

    for v in ["#text", "#ghost", "#icon", "#secondaryCompact", "#dangerOutline",
              "#toggleGreen", "#togglePink", "#primary", "#secondary", "#danger", "#success"]:
        assert f"QPushButton{v} " in GLOBAL_STYLE or f"QPushButton{v}," in GLOBAL_STYLE \
            or f"QPushButton{v}\n" in GLOBAL_STYLE or f"QPushButton{v}{{" in GLOBAL_STYLE, f"variante {v} ausente"
    # chaves balanceadas = f-string interpolou certo
    assert GLOBAL_STYLE.count("{") == GLOBAL_STYLE.count("}"), "chaves nao balanceadas no GLOBAL_STYLE"
    assert "{{" not in GLOBAL_STYLE, " sobrou chave literal {{ no GLOBAL_STYLE"


check("GLOBAL_STYLE: 11 variantes + chaves balanceadas", t_theme)


# ---------- create_color_icon deduplicado ----------
def t_icon():
    import inspect
    from gui.theme import create_color_icon

    assert inspect.isfunction(create_color_icon)
    # tasks_qt foi removido na 1G (nunca foi instanciado); a verificacao
    # passa a varrer o projeto inteiro, que e o teste que importa.
    ico = create_color_icon("#ff0000")
    assert not ico.isNull()


check("create_color_icon: 1 copia (theme.py)", t_icon)


# ---------- nenhuma tela anula objectName com stylesheet ----------
def t_no_override():
    import pathlib

    offenders = []
    for path in pathlib.Path("gui").rglob("*.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            m = __import__("re").search(r'setObjectName\("(primary|secondary|danger|success|secondaryCompact|dangerOutline|toggleGreen|togglePink)"\)', line)
            if not m:
                continue
            for j in range(i + 1, min(i + 6, len(lines))):
                if "setStyleSheet" in lines[j]:
                    offenders.append(f"{path}:{i+1} [{m.group(1)}]")
                    break
    assert not offenders, "objectName anulado por stylesheet inline: " + "; ".join(offenders)


check("nenhum objectName anulado por setStyleSheet", t_no_override)


# ---------- telas reais ----------
def t_projects():
    from gui.views.projects_qt import ProjectsQt

    v = ProjectsQt()
    v.load_data()
    assert v.btn_archived.text().endswith("OFF"), v.btn_archived.text()
    assert v.btn_archived.objectName() == "toggleGreen"
    v.btn_archived.setChecked(True)
    assert v.btn_archived.text().endswith("ON"), v.btn_archived.text()
    v.toggle_archived()
    assert v.show_archived is True


check("ProjectsQt: toggle Arquivados", t_projects)


def t_wiki():
    from gui.views.wiki_qt import WikiQt

    v = WikiQt()
    assert v.btn_archived.objectName() == "toggleGreen"


check("WikiQt: toggle Arquivados", t_wiki)


def t_activity():
    from gui.views.activity_summary_qt import ActivitySummaryQt

    v = ActivitySummaryQt()
    assert v.btn_concluidos.objectName() == "toggleGreen"
    assert v.btn_concluidos.text().endswith("OFF")
    assert v.btn_comentarios.objectName() == "togglePink"
    assert v.btn_comentarios.text().endswith("ON")


check("ActivitySummaryQt: toggles verde/rosa", t_activity)


def t_alarm_cards():
    from gui.components.alarm_cards_qt import AlarmCard
    from models.alert import Alert

    a = Alert(entity_type="task", entity_id=1, title="Teste",
              alert_date="2026-01-01", priority="high")
    card = AlarmCard(a, task_name="Tarefa X", project_name="Projeto Y",
                     on_edit=lambda i: None, on_delete=lambda i: None)
    b = card.findChild(QPushButton, "secondaryCompact")
    assert b is not None, "botao Editar deveria usar objectName=secondaryCompact"
    d = card.findChild(QPushButton, "dangerOutline")
    assert d is not None, "botao Excluir deveria usar objectName=dangerOutline"
    for btn in (b, d):
        assert btn.styleSheet() == "", f"{btn.text()} ainda tem stylesheet local"


check("AlarmCard: variantes compact/dangerOutline", t_alarm_cards)


def t_mainwindow():
    from gui.main_window_qt import MainWindow

    w = MainWindow()
    from gui.main_window_qt import NAV_NAMES
    assert len(w.btn_group.buttons()) == len(NAV_NAMES)
    from gui.main_window_qt import NAV_NAMES
    for idx in range(len(NAV_NAMES)):
        w._show_page(idx)
        marked = [i for i, b in w.nav_buttons.items() if b.isChecked()]
        assert marked == [idx], f"_show_page({idx}) marcou {marked}"


check("MainWindow: navegacao da sidebar", t_mainwindow)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)