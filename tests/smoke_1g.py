"""Etapa 1G: guarda contra o codigo morto voltar.

Verifica tres coisas:

1. Nenhum modulo importa tkinter/customtkinter. A UI e 100% PySide6 e o
   CentralDeGestao.spec EXCLUI tkinter da build -- se alguem importar de
   novo, o EXE quebra em runtime sem erro de build.

2. Nenhum hiddenimport do spec aponta para arquivo inexistente. O
   PyInstaller falha no build se nao achar um hiddenimport.

3. As views registradas na sidebar existem de fato, e nenhuma view orfa
   ficou no diretorio.
"""
import ast
import os
import re
import sys
import pathlib

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

RAIZ = pathlib.Path(os.getcwd())
ok, fail = [], []


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


def arquivos_py():
    return [p for p in RAIZ.rglob("*.py")
            if not any(x in p.parts for x in
                       ("venv_build", "build", "dist", "__pycache__", ".git"))]


def t_sem_tkinter():
    """Nenhum modulo pode importar tkinter/customtkinter: nao esta em
    requirements.txt e o spec exclui da build."""
    ofensas = []
    for p in arquivos_py():
        try:
            arvore = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError:
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                mods = [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom):
                mods = [no.module or ""]
            else:
                continue
            for m in mods:
                if m.split(".")[0] in ("tkinter", "customtkinter"):
                    ofensas.append(f"{p.relative_to(RAIZ)}:{no.lineno} -> {m}")
    assert not ofensas, "import de tkinter/customtkinter (quebraria a build): " \
                        + "; ".join(ofensas)


check("nenhum modulo importa tkinter/customtkinter", t_sem_tkinter)


def t_spec_aponta_para_arquivos_existentes():
    spec = RAIZ / "CentralDeGestao.spec"
    if not spec.exists():
        raise AssertionError("CentralDeGestao.spec nao encontrado")
    texto = spec.read_text(encoding="utf-8")
    ini = texto.index("hiddenimports=[")
    bloco = texto[ini:texto.index("]", ini)]
    faltando = []
    for m in re.findall(r"'([\w\.]+)'", bloco):
        if "." not in m:
            continue
        # PySide6.* e sqlite3 nao sao arquivos do projeto
        if m.startswith("PySide6") or m in ("sqlite3",):
            continue
        cand = RAIZ / (m.replace(".", os.sep) + ".py")
        cand_pkg = RAIZ / m.replace(".", os.sep) / "__init__.py"
        if not cand.exists() and not cand_pkg.exists():
            faltando.append(m)
    assert not faltando, "hiddenimport do spec sem arquivo: " + ", ".join(sorted(set(faltando)))


check("spec: todo hiddenimport aponta para arquivo existente", t_spec_aponta_para_arquivos_existentes)


def t_views_do_sidebar_existem():
    """As telas da sidebar precisam existir e poder ser instanciadas."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    from gui.theme import GLOBAL_STYLE
    app.setStyleSheet(GLOBAL_STYLE)

    # As telas sao lidas de NAV_PAGES (fonte unica de verdade) em vez de
    # uma lista fixa aqui: antes este teste citava workbench_qt (Monitor),
    # que foi removido da sidebar.
    from gui.main_window_qt import MainWindow, NAV_PAGES
    for _emoji, _nome, spec in NAV_PAGES:
        __import__(spec.split(":")[0])
    w = MainWindow()
    assert len(w.nav_buttons) == len(NAV_PAGES), \
        f"sidebar com {len(w.nav_buttons)} botoes (esperado {len(NAV_PAGES)})"
    for idx in w.nav_buttons:
        w._show_page(idx)
        marcados = [i for i, b in w.nav_buttons.items() if b.isChecked()]
        assert marcados == [idx], f"pagina {idx} marcou {marcados}"


check("sidebar: as telas existem e navegam", t_views_do_sidebar_existem)


def t_sem_views_orfas():
    """Nenhuma view inteira (arquivo em gui/views) pode ficar sem uso.

    Classes auxiliares definidas dentro do proprio modulo e usadas nele
    (ClickableFrame, WikiTreeWidget, _NewPageDialog) sao legitimas.
    """
    orfas = []
    todos = arquivos_py()
    for p in (RAIZ / "gui" / "views").glob("*.py"):
        usos = 0
        for q in todos:
            if q == p:
                continue
            src = q.read_text(encoding="utf-8", errors="ignore")
            if re.search(rf"gui\.views\.{p.stem}\b", src) or \
               re.search(rf"from gui\.views import .*\b{p.stem}\b", src):
                usos += 1
        if usos == 0:
            orfas.append(p.name)
    assert not orfas, "view sem uso: " + ", ".join(orfas)


check("nenhuma view orfa em gui/views", t_sem_views_orfas)


def t_componentes_importam():
    """Todo componente do diretorio tem que ser importavel (tkinter fora)."""
    falhas = []
    for p in sorted((RAIZ / "gui" / "components").glob("*.py")):
        if p.name == "__init__.py":
            continue
        mod = f"gui.components.{p.stem}"
        try:
            __import__(mod)
        except Exception as e:
            falhas.append(f"{mod}: {type(e).__name__}: {e}")
    assert not falhas, "componente nao importa: " + "; ".join(falhas)


check("todos os componentes de gui/components importam", t_componentes_importam)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)