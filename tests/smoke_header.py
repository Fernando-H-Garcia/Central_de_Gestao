import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication, QSizePolicy
from PySide6.QtCore import QEventLoop, QTimer

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


def settle(w, ms=220):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    app.processEvents()


def t_elide():
    from gui.components.page_header import ElidedTitle
    from PySide6.QtWidgets import QSizePolicy

    # modo padrao: quebra linha (comportamento original), com teto
    t = ElidedTitle("Um titulo bastante longo para precisar de quebrar linha")
    assert t.wordWrap() is False, "a quebra e feita pelo componente, nao pelo Qt"
    assert t.sizePolicy().horizontalPolicy() == QSizePolicy.Expanding
    assert t.toolTip() == t.full_text()
    t.resize(300, 30)
    t._refresh()
    assert "\n" in t.text(), f"deveria ter quebrado linha, veio {t.text()!r}"

    # teto de linhas: um titulo enorme nao pode empurrar o conteudo
    grande = ElidedTitle("palavra " * 200)
    grande.resize(300, 30)
    grande._refresh()
    n = grande.text().count("\n") + 1
    assert n <= 2, f"titulo quebrou em {n} linhas (teto e 2)"
    assert grande.text().endswith("…") or n == 2
    assert len(grande.text()) < len(grande.full_text())

    # modo elide: trunca numa linha
    e = ElidedTitle("Um titulo bastante longo para precisar de elisao", wrap=False)
    e.resize(200, 28)
    e._refresh()
    assert e.wordWrap() is False
    assert e.text().endswith("...") or e.text().endswith("…"), e.text()
    assert len(e.text()) < len(e.full_text())
    assert e.sizePolicy().horizontalPolicy() == QSizePolicy.Ignored
    assert e.minimumWidth() >= 200


check("ElidedTitle: quebra em ate 2 linhas ou elide (wrap=False)", t_elide)


def t_botao_no_extremo_direito():
    from services.project_service import ProjectService
    from gui.views.project_360_qt import Project360Qt

    ps = ProjectService().get_all_active()
    v = Project360Qt(ps[0].id)
    v.resize(1400, 800)
    v.show()
    settle(v)
    v.load_data()

    # O bloco da direita deve encostar na borda DIREITA do cabecalho.
    # A "folga" medida contra a view inclui a margem dela (20+20).
    h = v.header
    folga = h.width() - (v.btn_edit.x() + v.btn_edit.width())
    assert folga <= 8, f"{folga}px de folga no cabecalho (bloco nao encosta na borda)"
    assert v.btn_edit.x() > v.refs_panel.x(), "botao deve vir DEPOIS do painel"


check("360: painel e botao encostam na borda direita", t_botao_no_extremo_direito)


def t_titulo_nunca_some():
    from services.task_service import TaskService
    from gui.views.task_detail_qt import TaskDetailQt

    ts = TaskService().get_all_active()
    v = TaskDetailQt(ts[0].id)
    v.resize(1100, 800)
    v.show()
    settle(v)
    v.lbl_title.setText("Tarefa #1: " + "titulo absurdamente longo " * 8)
    settle(v)

    larg = v.lbl_title.width()
    fm = v.lbl_title.fontMetrics()
    linhas = v.lbl_title.height() // max(1, fm.height())
    print(f"   [diag] janela={v.width()} cabecalho={v.header.width()} titulo={larg} "
          f"altura={v.lbl_title.height()} linhas={linhas} "
          f"refs={v.refs_panel.width()} btn={v.btn_edit.width()}")
    assert larg >= 400, f"titulo espremido para {larg}px (antes ficava 200)"
    exibido = v.lbl_title.text()
    assert exibido, "titulo ficou vazio"
    assert v.lbl_title.toolTip(), "sem tooltip para o texto completo"
    # altura coerente: quebra em poucas linhas, nao dezenas
    assert linhas <= 3, f"titulo quebrou em {linhas} linhas (espremido)"
    assert len(exibido) < len(v.lbl_title.full_text()) or "\n" in exibido


check("detalhe: titulo longo quebra linha e nao some", t_titulo_nunca_some)


def t_painel_nao_infla():
    """O painel de Referencias precisa ser compacto. Com os rotulos por
    extenso ele media 462px e espremia o titulo a ~200px."""
    from gui.components.references_panel_qt import ReferencesPanelQt

    p = ReferencesPanelQt(entity_type="project", entity_id=17)
    p.show()
    app.processEvents()
    assert p.width() <= 160, f"painel de referencias em {p.width()}px (era 462)"
    for b in (p.btn_out, p.btn_in):
        assert b.sizePolicy().horizontalPolicy() == QSizePolicy.Fixed
        assert len(b.text()) <= 5, f"rotulo longo de novo: {b.text()!r}"
        assert b.toolTip(), "precisa de tooltip com o texto completo"


check("painel de referencias: compacto (<=160px), com tooltip", t_painel_nao_infla)


def t_projects_header_ok():
    """ProjectsQt usa PageHeader com botoes, sem painel -- nao pode quebrar."""
    from gui.views.projects_qt import ProjectsQt

    v = ProjectsQt()
    v.resize(1200, 800)
    v.show()
    settle(v)
    assert v.btn_archived.objectName() == "toggleGreen"
    assert v.btn_new.objectName() == "secondary"


check("ProjectsQt: cabecalho com botoes continua ok", t_projects_header_ok)


def t_titulo_aparece_ao_abrir():
    """Regressao: o titulo precisa ser montado em load_data().

    showEvent chama load_data(), nao safe_load_data(). O titulo vinha do
    construtor do QLabel e, ao migrar para PageHeader(), foi perdido --
    a tela abria com o titulo vazio e nao dava para identificar a tarefa.
    """
    from services.task_service import TaskService
    from gui.views.task_detail_qt import TaskDetailQt

    ts = TaskService().get_all_active()
    v = TaskDetailQt(ts[0].id)
    v.resize(1100, 800)
    v.show()
    settle(v)

    assert v.lbl_title.full_text(), "titulo VAZIO ao abrir a tarefa"
    assert v.lbl_title.text(), "titulo nao e desenhado"
    assert str(v.task.id) in v.lbl_title.full_text()
    assert v.lbl_title.objectName() == "headerEntity", v.lbl_title.objectName()

    from models.entities import Task
    v.task = Task(id=v.task.id, title="Titulo alterado", project_id=v.task.project_id)
    v.load_data()
    settle(v)
    assert "alterado" in v.lbl_title.full_text()


check("detalhe: titulo aparece ao abrir e ao renomear", t_titulo_aparece_ao_abrir)


def t_titulo_que_cabe_nao_trunca():
    """Um titulo que CABE na largura nao pode ganhar reticencias."""
    from services.task_service import TaskService
    from gui.views.task_detail_qt import TaskDetailQt

    ts = TaskService().get_all_active()
    v = TaskDetailQt(ts[0].id)
    v.resize(1100, 800)
    v.show()
    settle(v)
    exibido, completo = v.lbl_title.text(), v.lbl_title.full_text()
    assert "…" not in exibido and "..." not in exibido, f"titulo curto truncado: {exibido!r}"
    assert " ".join(exibido.split()) == " ".join(completo.split())


check("detalhe: titulo que cabe aparece inteiro", t_titulo_que_cabe_nao_trunca)


def t_360_fonte_entidade():
    from services.project_service import ProjectService
    from gui.views.project_360_qt import Project360Qt

    ps = ProjectService().get_all_active()
    v = Project360Qt(ps[0].id)
    v.resize(1400, 800)
    v.show()
    settle(v)
    v.load_data()
    settle(v)
    assert v.lbl_title.full_text(), "titulo do 360 vazio"
    assert v.lbl_title.objectName() == "headerEntity"


check("360: titulo preenchido com fonte de entidade", t_360_fonte_entidade)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)