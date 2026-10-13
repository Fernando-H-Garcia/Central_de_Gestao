"""Sidebar sem 'Monitor' e com fonte unica de verdade.

Verifica o que quebraria silenciosamente ao remover um item da sidebar:
o numero de paginas, os rotulos do historico e o indice fixo que apontava
para 'Documentacao'.
"""
import os
import sys

os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
from gui.theme import GLOBAL_STYLE, LightBranchStyle
app.setStyleSheet(GLOBAL_STYLE)
app.setStyle(LightBranchStyle())

results = []


def check(nome, cond, extra=""):
    results.append((nome, bool(cond)))
    print(f"  {'ok  ' if cond else 'FALHA'} {nome}" + (f"  -> {extra}" if extra else ""))


import gui.main_window_qt as mw

print("=== fonte unica ===")
nomes = mw.NAV_NAMES
print(f"    NAV_PAGES = {nomes}")
check("Monitor removido", "Monitor" not in nomes)
check("Projetos presente", "Projetos" in nomes)
check("Documentacao presente", "Documenta\u00e7\u00e3o" in nomes)
check("4 paginas", len(nomes) == 4, str(len(nomes)))
check("sem nomes duplicados", len(nomes) == len(set(nomes)))

print("\n=== indices coerentes ===")
idx_doc = nomes.index("Documenta\u00e7\u00e3o")
check("Documentacao e o ultimo indice", idx_doc == len(nomes) - 1, str(idx_doc))
check("Projetos agora e o indice 0", nomes.index("Projetos") == 0)
# o bug antigo: change_page(4) apontava para Documentacao (indice 4 de 5).
# Depois de remover o Monitor, o indice 4 nao existe mais.
check("indice fixo 4 saiu de faixa (bug antigo evitado)", idx_doc != 4)

print("\n=== _page_index resolve pelo nome ===")
win = mw.MainWindow.__new__(mw.MainWindow)
check("_page_index(Documentacao)", win._page_index("Documenta\u00e7\u00e3o") == idx_doc)
check("_page_index(Projetos)", win._page_index("Projetos") == 0)
check("nome inexistente cai em 0 (nao quebra)", win._page_index("Inexistente") == 0)

print("\n=== rotulos do historico usam a fonte unica ===")
for i, esperado in enumerate(nomes):
    got = win._label_for_target(("page", i))
    check(f"rotulo[{i}] = {esperado}", got == esperado, got)
check("rotulo fora de faixa nao quebra", isinstance(win._label_for_target(("page", 99)), str))

print("\n=== os 4 views declarados existem e importam ===")
import importlib
for emoji, nome, spec in mw.NAV_PAGES:
    mod, cls = spec.split(":")
    m = importlib.import_module(mod)
    ok = hasattr(m, cls)
    check(f"{nome}: {cls} existe", ok)

print("\n=== WorkbenchQt saiu do projeto ===")
try:
    importlib.import_module("gui.views.workbench_qt")
    check("workbench_qt nao importa mais", False, "ainda existe")
except ModuleNotFoundError:
    check("workbench_qt nao importa mais", True)

print("\n=== monta a MainWindow de verdade (pega erro de desempacotamento) ===")
# Esta parte faltava: as checagens acima so olhavam a lista NAV_PAGES e
# deixavam passar um erro no laco que constroi a janela (ja aconteceu:
# "for _i, _emoji, item, spec" com NAV_PAGES de 3 campos -> ValueError).
import shutil
from pathlib import Path
import config

_tmp = Path(os.environ["TEMP"]) / "smoke_sidebar.db"
shutil.copy2(Path("database/novo_cerebro.db"), _tmp)
config.DB_PATH = _tmp

from gui.main_window_qt import MainWindow
win = MainWindow()
win.show()
app.processEvents()
check("janela montou sem excecao", True)
check("stacked_widget tem uma pagina por NAV_PAGES",
      win.stacked_widget.count() == len(nomes),
      f"{win.stacked_widget.count()} vs {len(nomes)}")
check("um botao por pagina", len(win.nav_buttons) == len(nomes),
      f"{len(win.nav_buttons)} vs {len(nomes)}")

classes = []
for i in range(win.stacked_widget.count()):
    win.change_page(i)
    app.processEvents()
    classes.append(type(win.stacked_widget.widget(i)).__name__)
    assert win.stacked_widget.currentIndex() == i
    assert win.nav_buttons[i].isChecked(), f"botao {i} nao marcou"
print(f"    paginas: {classes}")
check("navegar por indice marca o botao e troca a pagina", True)
check("pagina 0 e Projetos", classes[0] == "ProjectsQt", classes[0])
check("pagina 1 e Resumo das Atividades",
      classes[1] == "ActivitySummaryQt", classes[1])
check("pagina 2 e Agenda Geral", classes[2] == "AgendaQt", classes[2])
check("pagina 3 e Documentacao", classes[3] == "WikiQt", classes[3])

idx = win._page_index("Documenta\u00e7\u00e3o")
win._show_page(idx)
app.processEvents()
check("_page_index leva a pagina certa",
      win.stacked_widget.currentIndex() == idx == len(nomes) - 1, str(idx))
win.close()

print("\n=== nenhum change_page com indice literal ===")
# Checagem por AST: comments mencionam 'change_page(4)' ao explicar o bug,
# e texto nao distingue comment de codigo executavel.
import ast, inspect
arvore = ast.parse(inspect.getsource(mw))
literais = []
for node in ast.walk(arvore):
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "change_page" and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, int)):
        literais.append((node.lineno, node.args[0].value))
check("nenhum change_page(<numero>) no codigo", not literais, str(literais))
check("usa _page_index no lugar", "_page_index(" in inspect.getsource(mw))

ok = sum(1 for _, c in results if c)
print(f"\n{ok} ok / {len(results) - ok} fail")
sys.exit(0 if ok == len(results) else 1)