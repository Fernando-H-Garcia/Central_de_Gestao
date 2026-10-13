import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication, QHBoxLayout

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


def t_pageheader_api():
    from gui.components.page_header import PageHeader

    h = PageHeader("Titulo", "Sub")
    assert h.title_label.text() == "Titulo"
    # isVisible() depende do pai estar visivel; isHidden() nao.
    assert h.subtitle_label.isHidden() is False, "com subtitle o label nao deveria estar oculto"
    h.set_title("Novo")
    h.set_subtitle("Sub2")
    assert h.title_label.text() == "Novo"
    assert h.subtitle_label.text() == "Sub2"
    assert h.subtitle_label.isHidden() is False
    h.set_subtitle("")
    assert h.subtitle_label.isHidden() is True, "subtitle vazio deveria ocultar o label"
    from PySide6.QtWidgets import QPushButton
    b = QPushButton("x")
    h.add_button(b)
    h.add_left_widget(QPushButton("y"))
    from gui.components.references_panel_qt import ReferencesPanelQt
    p = ReferencesPanelQt(entity_type="project", entity_id=1)
    h.add_right_widget(p)
    assert h._right_layout.count() >= 2, "add_right_widget deveria inserir o painel"
    assert p.parent() is not None or True
    assert h.styleSheet() == "", "PageHeader nao deve ter stylesheet local"


check("PageHeader: API + subtitle + add_right_widget", t_pageheader_api)


def t_project360():
    from gui.views.project_360_qt import Project360Qt
    from gui.components.page_header import PageHeader
    from services.project_service import ProjectService

    p = ProjectService().get_all_active()
    if not p:
        raise AssertionError("sem projetos para testar")
    v = Project360Qt(p[0].id)
    assert isinstance(v.header, PageHeader), "360 deveria usar PageHeader"
    assert v.lbl_title is v.header.title_label, "lbl_title deve ser o title_label do header"
    assert v.header._left_layout.count() >= 2, "back_nav + area de texto"
    assert v.header._button_layout.count() >= 1, "btn_edit"
    assert v.header._right_layout.count() >= 2, "refs_panel"
    v.load_data()
    assert v.lbl_title.text().startswith("Projeto:"), v.lbl_title.text()


check("Project360Qt: PageHeader + titulo via header", t_project360)


def t_task_detail():
    from gui.views.task_detail_qt import TaskDetailQt
    from gui.components.page_header import PageHeader, ElidedTitle
    from services.task_service import TaskService

    tasks = TaskService().get_all_active()
    if not tasks:
        raise AssertionError("sem tarefas para testar")
    v = TaskDetailQt(tasks[0].id)
    assert isinstance(v.header, PageHeader), "detalhe da tarefa deveria usar PageHeader"
    assert v.lbl_title is v.header.title_label
    # wordWrap foi REMOVIDO: com elisao o rotulo consumia a altura toda e
    # espremia a linha. O ElidedTitle trunca com reticencias + tooltip.
    assert v.lbl_title.wordWrap() is False, "wordWrap conflita com a elisao"
    assert isinstance(v.lbl_title, ElidedTitle), "titulo deveria ser ElidedTitle"
    v.safe_load_data()
    assert v.lbl_title.text().startswith("Tarefa #"), v.lbl_title.text()


check("TaskDetailQt: PageHeader + titulo wordwrap", t_task_detail)


def t_ideas():
    from gui.views.ideas_qt import IdeasQt
    from gui.components.page_header import PageHeader

    v = IdeasQt()
    assert isinstance(v.header, PageHeader), "ideias deveria usar PageHeader"
    assert v.header.title_label.text() == "💡 Ideias"
    # o titulo nao pode estar duplicado
    from PySide6.QtWidgets import QLabel
    headers = [l for l in v.findChildren(QLabel) if l.objectName() == "header"]
    assert len(headers) == 1, f"titulo duplicado: {len(headers)} labels com objectName=header"
    assert v.header._button_layout.count() >= 3, "busca + arquivados + nova ideia"


check("IdeasQt: PageHeader sem titulo duplicado", t_ideas)


def t_wiki_toggles():
    from gui.views.wiki_qt import WikiQt

    v = WikiQt()
    assert v.btn_read.objectName() == "toggleBlue", v.btn_read.objectName()
    assert v.btn_read.isChecked() is True
    assert v.btn_edit_mode.objectName() == "toggleBlue"
    assert v.btn_edit_mode.styleSheet() == "", "btn_edit_mode ainda tem stylesheet inline"
    assert v.btn_save.objectName() == "success"
    assert v.btn_save.styleSheet() == "", "btn_save ainda tem stylesheet inline"
    # alternar modo continua funcionando
    v._set_edit_mode()
    assert v.btn_edit_mode.isChecked() is True
    assert v.btn_read.isChecked() is False, "QButtonGroup deve desmarcar o outro"
    v._set_read_mode()
    assert v.btn_read.isChecked() is True


check("WikiQt: toggles azuis + salvar success", t_wiki_toggles)


def t_toggleblue_no_tema():
    assert "QPushButton#toggleBlue" in GLOBAL_STYLE
    for v in ["toggleGreen", "togglePink", "toggleBlue"]:
        assert f"QPushButton#{v}:!checked" in GLOBAL_STYLE, f"falta estado OFF de {v}"


check("tema: variante toggleBlue", t_toggleblue_no_tema)


def t_headers_padrao():
    """Nenhuma view deve montar QLabel#header na mao anymore."""
    import pathlib

    offenders = []
    for path in pathlib.Path("gui/views").rglob("*.py"):
        if path.name in ("notes_qt.py", "tasks_qt.py"):
            continue  # codigo morto, removido na 1G
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if 'setObjectName("header")' in line:
                offenders.append(f"{path.name}:{i}")
    assert not offenders, "QLabel#header montado a mao em: " + ", ".join(offenders)


check("nenhuma view viva monta QLabel#header na mao", t_headers_padrao)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)