"""Regressao: stylesheet local em um ANCESTRAL desliga as regras do
GLOBAL_STYLE nos descendentes.

Foi exatamente isso que deixou os cards (#card) transparentes: o QScrollArea
da ProjectsQt e o editor_container da Wiki tinham setStyleSheet local, e
a regra QFrame#card do tema deixava de casar nos filhos.

Este teste renderiza de verdade e compara pixels -- nao basta verificar
objectName/stylesheet, porque o sintoma so aparece na pintura.
"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import QEventLoop, QTimer, QPoint
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget, QVBoxLayout

app = QApplication(sys.argv)

from gui.theme import GLOBAL_STYLE, BG_CARD, BG_PRIMARY
from gui.components.card import Card

app.setStyleSheet(GLOBAL_STYLE)

ok, fail = [], []


def settle(ms=250):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    app.processEvents()


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


def paints(widget, view=None):
    """True se o widget pinta BG_CARD (delta >= 20 do fundo da pagina)."""
    target = view if view is not None else widget
    img = target.grab().toImage()
    o = widget.mapTo(target, QPoint(0, 0))
    x = o.x() + widget.width() // 2
    y = o.y() + widget.height() // 2
    c = img.pixelColor(x, y)
    got = (c.red(), c.green(), c.blue())
    exp = (int(BG_CARD[1:3], 16), int(BG_CARD[3:5], 16), int(BG_CARD[5:7], 16))
    return sum(abs(a - b) for a, b in zip(got, exp)) <= 24, "#%02x%02x%02x" % got


def t_scroll_sem_qss_local():
    """O cenario que quebrava: QScrollArea com stylesheet local."""
    host = QWidget()
    host.resize(500, 300)
    v = QVBoxLayout(host)
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    inner = QWidget()
    iv = QVBoxLayout(inner)
    card = Card()
    iv.addWidget(card)
    sa.setWidget(inner)
    v.addWidget(sa)
    host.show()
    settle()
    good, got = paints(card, host)
    assert good, f"card dentro de QScrollArea SEM qss local nao pintou (pixel {got})"
    host.deleteLater()


check("baseline: QScrollArea sem stylesheet local -> card pinta", t_scroll_sem_qss_local)


def t_sem_qss_local_em_ancestral():
    """Nenhum QScrollArea/QWidget de container pode ter stylesheet local.

    Se um deles tiver, os cards dentro ficam transparentes. A regra
    `QScrollArea { background: transparent; border: none }` ja existe no
    GLOBAL_STYLE, entao o stylesheet local e sempre redundante.
    """
    import pathlib

    offenders = []
    for path in pathlib.Path("gui").rglob("*.py"):
        if path.name == "theme.py":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if "setStyleSheet" not in line:
                continue
            alvo = lines[i - 1] if i else ""
            # container com filhos: QScrollArea ou QWidget em atribuido
            if ("QScrollArea()" in alvo or "QWidget()" in alvo
                    or "editor_container" in alvo or "col_widget" in alvo):
                offenders.append(f"{path}:{i + 1}  <- {alvo.strip()}")
    assert not offenders, ("stylesheet local em container (quebra os filhos): "
                           + "; ".join(offenders))


check("nenhum container (QScrollArea/QWidget) com stylesheet local", t_sem_qss_local_em_ancestral)


def t_card_projects_pinta():
    from gui.views.projects_qt import ProjectsQt
    from gui.components.card import Card

    v = ProjectsQt()
    v.resize(1200, 900)
    v.show()
    settle()
    cards = [c for c in v.findChildren(Card) if c.objectName() == "clickableCard"]
    assert cards, "nenhum clickableCard encontrado na ProjectsQt"
    good, got = paints(cards[0], v)
    assert good, f"card de projeto transparente (pixel {got}, esperado {BG_CARD})"


check("ProjectsQt: card de projeto PINTA o fundo do tema", t_card_projects_pinta)


def t_cards_wiki_pintam():
    from gui.views.wiki_qt import WikiQt
    from gui.components.card import Card

    v = WikiQt()
    v.resize(1400, 900)
    v.show()
    settle()
    cards = [c for c in v.findChildren(Card) if c.objectName() == "card"]
    assert len(cards) >= 2, f"esperava 2 cards na WikiQt, achei {len(cards)}"
    for i, c in enumerate(cards, 1):
        good, got = paints(c, v)
        assert good, f"card #{i} da wiki transparente (pixel {got}, esperado {BG_CARD})"


check("WikiQt: meta bar e painel de anexos PINTAM", t_cards_wiki_pintam)


def t_borda_e_hover():
    assert "QFrame#card {" in GLOBAL_STYLE
    card_block = GLOBAL_STYLE[GLOBAL_STYLE.index("QFrame#card {"):
                              GLOBAL_STYLE.index("QFrame#clickableCard")]
    assert "border:" in card_block, "QFrame#card sem borda (a borda sumia contra o fundo)"
    click = GLOBAL_STYLE[GLOBAL_STYLE.index("QFrame#clickableCard"):
                         GLOBAL_STYLE.index("QFrame#Sidebar")]
    assert "QFrame#clickableCard:hover" in click, "card clicavel sem hover"


check("tema: card com borda + hover no clicavel", t_borda_e_hover)


def t_card_tem_styledbg():
    from gui.components.card import Card as C
    from PySide6.QtCore import Qt
    assert C().testAttribute(Qt.WA_StyledBackground), "Card sem WA_StyledBackground"


check("Card: WA_StyledBackground ligado", t_card_tem_styledbg)

print("=" * 66)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 66)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)