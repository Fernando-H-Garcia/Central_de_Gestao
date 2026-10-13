import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor

app = QApplication(sys.argv)

from gui.theme import (GLOBAL_STYLE, ACCENT_BLUE, SUCCESS_GREEN,
                       ERROR_RED, WARNING_ORANGE, BG_CARD)

app.setStyleSheet(GLOBAL_STYLE)

ok, fail = [], []


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


def bar_color(bar, pct=None):
    """Le a cor REAL pintada na barra.

    O texto (branco) e desenhado CENTRALIZADO, entao amostrar no meio
    pega a letra. Varre alguns pontos e devolve o primeiro que nao seja
    texto -- ou seja, a cor do preenchimento.
    """
    img = bar.grab().toImage()
    p = 100 if pct is None else pct
    fill_w = img.width() * (p / 100)
    y = img.height() // 2
    last = None
    for frac in (0.25, 0.35, 0.20, 0.45, 0.10, 0.60, 0.75):
        x = int(fill_w * frac)
        if x < 0 or x >= img.width():
            continue
        c = img.pixelColor(x, y)
        last = f"#{c.red():02x}{c.green():02x}{c.blue():02x}"
        if not (c.red() > 200 and c.green() > 200 and c.blue() > 200):
            return last
    return last or "#000000"


def near(a, b, tol=26):
    ca, cb = QColor(a), QColor(b)
    return sum(abs(x - y) for x, y in zip(ca.getRgb()[:3], cb.getRgb()[:3])) <= tol


def t_cor_nao_depende_da_porcentagem():
    """A COR NAO pode mais vir da %. Um projeto em 10% e normal."""
    from gui.components.progress_bar import ProgressBar
    from gui.theme import BG_CARD

    # de 1% a 100%: sempre azul neutro. Em 0% nao ha preenchimento, entao
    # sobra so o fundo da barra (comportamento correto).
    for pct in (1, 10, 35, 50, 75, 99, 100):
        b = ProgressBar(pct, 100)
        b.resize(400, 20)
        got = bar_color(b, pct)
        assert near(got, ACCENT_BLUE), f"{pct}% pintou {got}, esperado azul neutro {ACCENT_BLUE}"
    zero = bar_color(ProgressBar(0, 100), 0)
    assert near(zero, BG_CARD), f"0% pintou {zero}, esperado so o fundo {BG_CARD}"

    # 100% so fica verde se a CHAMADA pedir explicitamente
    assert ProgressBar(100, 100)._color == ACCENT_BLUE, "100% nao deve virar verde sozinho"
    b = ProgressBar(100, 100)
    b.resize(400, 20)
    b.set_color(SUCCESS_GREEN)
    assert near(bar_color(b, 100), SUCCESS_GREEN), "set_color nao aplicou"


check("ProgressBar: cor NAO derivada da % (azul neutro em 1-100)", t_cor_nao_depende_da_porcentagem)


def t_api():
    from gui.components.progress_bar import ProgressBar, ProgressBarWithLabel

    b = ProgressBar(0, 100)
    assert b.value() == 0
    b.set_value(150)
    assert b.value() == 100, "set_value deve limitar no maximum"
    b.set_value(-10)
    assert b.value() == 0, "set_value nao pode ficar negativo"
    b.set_maximum(0)
    assert b._maximum == 1, "maximum nunca abaixo de 1 (divisao por zero)"
    assert abs(b.percentage() - b.value() / b._maximum * 100) < 1e-6
    b.set_text("50% (5/10)")
    assert b.sizeHint().height() == 20
    b.set_color(None)
    assert b._color == ACCENT_BLUE, "set_color(None) volta ao azul"

    w = ProgressBarWithLabel(30, 100)
    w.set_value(70)
    assert w._pct_label.text() == "70%", w._pct_label.text()
    w.set_color(SUCCESS_GREEN)
    assert w._inner._color == SUCCESS_GREEN, "com rotel deve repassar a cor"


check("ProgressBar: limites, texto, set_color, WithLabel", t_api)


def t_360_usa_componente():
    from gui.views.project_360_qt import Project360Qt
    from gui.components.progress_bar import ProgressBar
    from services.project_service import ProjectService

    ps = ProjectService().get_all_active()
    if not ps:
        raise AssertionError("sem projetos")
    v = Project360Qt(ps[0].id)
    assert isinstance(v.progress_bar, ProgressBar), "360 deveria usar o componente ProgressBar"
    assert v.progress_bar.styleSheet() == "", "sem stylesheet local"
    v.load_data()
    assert "%" in v.progress_bar._text, v.progress_bar._text
    pct = v.progress_bar.percentage()
    got = bar_color(v.progress_bar, pct if pct > 0 else 100)
    valid = any(near(got, c) for c in (ACCENT_BLUE, SUCCESS_GREEN, ERROR_RED, WARNING_ORANGE))
    assert valid, f"cor pintada {got} nao e nenhuma semantica valida"


check("Project360Qt: usa ProgressBar com cor semantica", t_360_usa_componente)


def t_semantica_360():
    """_progress_color segue a convencao do Gantt.

    A parte que depende do banco varia conforme os dados reais do projeto,
    entao aqui so se verifica: (a) o ramo "tudo concluido" que nao toca o
    banco, e (b) que o retorno e sempre uma das 4 cores semanticas.
    """
    from gui.views.project_360_qt import Project360Qt
    from gui.theme import ACCENT_BLUE, SUCCESS_GREEN, ERROR_RED, WARNING_ORANGE
    from services.project_service import ProjectService

    ps = ProjectService().get_all_active()
    v = Project360Qt(ps[0].id)

    # verde: tudo concluido (ramo que nao consulta tarefas)
    assert v._progress_color(4, 4) == SUCCESS_GREEN, "tudo concluido deve ser verde"
    assert v._progress_color(1, 1) == SUCCESS_GREEN

    # sem tarefas nao ha 100%, entao nao marca verde
    assert v._progress_color(0, 0) != SUCCESS_GREEN, "sem tarefas nao deve marcar verde"

    # qualquer combinacao devolve uma das 4 cores semanticas
    validas = {ACCENT_BLUE, SUCCESS_GREEN, ERROR_RED, WARNING_ORANGE}
    for total, done in [(10, 0), (10, 3), (10, 10), (0, 0), (5, 1), (1, 0)]:
        got = v._progress_color(total, done)
        assert got in validas, f"({total},{done}) devolveu {got}, fora da paleta semantica"


check("Project360Qt._progress_color: paleta e ramo concluído", t_semantica_360)


def t_texto_dentro_da_barra():
    b = None
    from gui.components.progress_bar import ProgressBar
    b = ProgressBar(60, 100, text="60% (6/10 Tarefas Concluídas)")
    b.resize(400, 20)
    img = b.grab().toImage()
    # procura algum pixel quase branco = o texto foi desenhado
    found = False
    for x in range(0, img.width(), 3):
        for y in range(0, img.height(), 2):
            c = img.pixelColor(x, y)
            if c.red() > 200 and c.green() > 200 and c.blue() > 200:
                found = True
                break
        if found:
            break
    assert found, "o texto nao foi desenhado dentro da barra"


check("ProgressBar: texto desenhado dentro da barra", t_texto_dentro_da_barra)


def t_sem_qprogressbar():
    """Nenhum uso REAL do QProgressBar nativo sobrou.

    Ignora comentario/docstring e o proprio modulo do componente, que
    menciona QProgressBar so para explicar o que substitui.
    """
    import pathlib
    import re

    h = []
    for p in pathlib.Path("gui").rglob("*.py"):
        if p.name == "progress_bar.py":
            continue
        src = p.read_text(encoding="utf-8")
        # tira comments e docstrings
        src = re.sub(r'""".*?"""', '', src, flags=re.S)
        src = re.sub(r"#.*", "", src)
        for i, l in enumerate(src.splitlines(), 1):
            if "QProgressBar" in l:
                h.append(f"{p}:{i}")
    assert not h, "QProgressBar ainda em uso: " + ", ".join(h)


check("nenhum QProgressBar (nativo) restante na UI", t_sem_qprogressbar)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)