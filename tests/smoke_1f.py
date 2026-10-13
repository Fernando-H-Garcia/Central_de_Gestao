import os
import re
import sys
import pathlib

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from gui.theme import GLOBAL_STYLE, ERROR_RED, SUCCESS_GREEN
app.setStyleSheet(GLOBAL_STYLE)

ok, fail = [], []


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


def t_api():
    from gui.components.context_menu_qt import ContextMenuQt, TASK_STATUSES

    m = ContextMenuQt(parent=None)
    a_open = m.add_command("👁️ Abrir")
    m.add_separator()
    sub = m.add_submenu("📊 Mudar Status")
    sub.add_status_items(on_click=lambda s: None)
    a_del = m.add_command("🗑️ Excluir", danger=True)

    assert a_open.text() == "👁️ Abrir"
    assert a_del.text() == "🗑️ Excluir", "danger nao pode alterar o rotulo"
    # Decisao do usuario: sem bolinha vermelha. Item de menu e texto puro.
    assert a_del.icon().isNull(), "item de menu nao deve levar icone de perigo"
    assert a_open.icon().isNull()
    assert len(sub.menu.actions()) == len(TASK_STATUSES) == 6
    for act in sub.menu.actions():
        assert not act.icon().isNull(), "todo item de status deve ter a bolinha"
    assert m.menu.styleSheet() == "", "ContextMenuQt nao deve ter stylesheet local"


check("ContextMenuQt: API, menu sem icone de perigo, status com bolinha", t_api)


def t_callback_isolado():
    """A classic lambda bug: item de submenu passa o valor errado."""
    from gui.components.context_menu_qt import ContextMenuQt

    m = ContextMenuQt(parent=None)
    sub = m.add_submenu("Status")
    sub.add_status_items(on_click=lambda s: escolhidos.append(s))
    # dispara todos, como o usuario faria
    for act in sub.menu.actions():
        act.trigger()

    assert escolhidos == ["Pendente", "Em Andamento", "Pausado",
                         "Aguardando", "Bloqueado", "Concluído"], escolhidos


escolhidos = []
check("lambda do submenu nao captura o valor errado", t_callback_isolado)


def t_callback_color():
    from gui.components.context_menu_qt import ContextMenuQt
    from gui.theme import get_energy_color

    m = ContextMenuQt(parent=None)
    sub = m.add_submenu("Prioridade")
    vals = []
    sub.add_color_items(["Baixa", "Média", "Alta", "Crítica"],
                        color_of=get_energy_color,
                        on_click=lambda p: vals.append(p))
    for act in sub.menu.actions():
        act.trigger()
    assert vals == ["Baixa", "Média", "Alta", "Crítica"], vals
    assert len(sub.menu.actions()) == 4


check("add_color_items: prioridade com a paleta certa", t_callback_color)


def t_proxy():
    """Call sites antigos (addAction/addSeparator/addMenu/exec) nao podem
    quebrar em runtime enquanto a migracao nao acabou."""
    from gui.components.context_menu_qt import ContextMenuQt

    m = ContextMenuQt(parent=None)
    m.addSeparator()
    act = m.addAction("estilo antigo")
    sub = m.addMenu("submenu antigo")
    assert sub is not None
    assert act is not None
    assert callable(m.exec)


check("proxy para o estilo QMenu antigo (addAction/addSeparator/addMenu)", t_proxy)


def t_nenhum_qmenu_cru():
    """Nenhuma view/componente constroi QMenu direto (fora do proprio
    componente e do menu persistente da toolbar de historico)."""
    crud = []
    for p in pathlib.Path("gui").rglob("*.py"):
        if p.name in ("context_menu_qt.py", "back_nav_widget_qt.py"):
            continue  # o componente, e o QMenu persistente de toolbar
        src = p.read_text(encoding="utf-8")
        src = re.sub(r'""".*?"""', '', src, flags=re.S)
        src = re.sub(r"#.*", "", src)
        for i, l in enumerate(src.splitlines(), 1):
            if re.search(r"=\s*QMenu\(", l):
                crud.append(f"{p.name}:{i}")
    assert not crud, "QMenu cru ainda em: " + ", ".join(crud)


check("nenhuma construcao direta de QMenu fora do componente", t_nenhum_qmenu_cru)


def t_create_color_icon_1copia():
    """A deduplicacao da 1B falhou antes em task_detail_qt (o teste
    antigo so olhava 2 arquivos). Varre o projeto inteiro."""
    crud = []
    for p in pathlib.Path("gui").rglob("*.py"):
        if p.name == "theme.py":
            continue  # a definicao canonica
        src = p.read_text(encoding="utf-8")
        src = re.sub(r'""".*?"""', '', src, flags=re.S)
        if "QPixmap(16, 16)" in src:
            crud.append(p.name)
    assert not crud, "create_color_icon reimplementado em: " + ", ".join(crud)


check("create_color_icon: 1 copia em todo o projeto", t_create_color_icon_1copia)


def t_lista_status_1copia():
    """A lista de status nao pode mais estar escrita a mao em varios
    lugares -- ela vem de TASK_STATUSES."""
    crud = []
    for p in pathlib.Path("gui").rglob("*.py"):
        if p.name == "context_menu_qt.py":
            continue
        src = p.read_text(encoding="utf-8")
        src = re.sub(r'""".*?"""', '', src, flags=re.S)
        src = re.sub(r"#.*", "", src)
        if '"Pendente", "Em Andamento", "Pausado"' in src:
            crud.append(f"{p.name}")
    assert not crud, "lista de status hardcoded em: " + ", ".join(crud)


check("lista de status: so TASK_STATUSES", t_lista_status_1copia)


def t_views_carregam():
    """Todas as telas com menu migrado ainda constroem."""
    from services.project_service import ProjectService
    from services.task_service import TaskService
    from gui.views.projects_qt import ProjectsQt
    from gui.views.wiki_qt import WikiQt
    from gui.views.agenda_qt import AgendaQt

    ProjectsQt()
    WikiQt()
    AgendaQt()

    ps = ProjectService().get_all_active()
    if ps:
        from gui.views.project_360_qt import Project360Qt
        from gui.views.ideas_qt import IdeasQt
        Project360Qt(ps[0].id)
        IdeasQt()
    ts = TaskService().get_all_active()
    if ts:
        from gui.views.task_detail_qt import TaskDetailQt
        TaskDetailQt(ts[0].id)


check("views com menu migrado constroem sem erro", t_views_carregam)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)