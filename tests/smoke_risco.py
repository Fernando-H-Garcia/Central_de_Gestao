import os
import sys
import datetime

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from gui.theme import GLOBAL_STYLE, ACCENT_BLUE, SUCCESS_GREEN, ERROR_RED, WARNING_ORANGE

app.setStyleSheet(GLOBAL_STYLE)

ok, fail = [], []


def check(name, fn):
    try:
        fn()
        ok.append(name)
    except Exception as e:
        fail.append(f"{name}: {type(e).__name__}: {e}")


def t_constante_unica():
    """O corte de risco nao pode estar escrito a mao em dois lugares."""
    import pathlib

    from gui.components.timeline.timeline_mapper import RISCO_DIAS

    assert RISCO_DIAS == 3, f"RISCO_DIAS mudou para {RISCO_DIAS}; o Gantt usava 3"

    # nenhum outro "<= 7" ou "<= 3" hardcoded para risco (ignorando
    # comentarios e docstrings, que legitimamente descrevem a regra)
    import re
    hard = []
    for p in list(pathlib.Path("gui").rglob("*.py")):
        src = p.read_text(encoding="utf-8")
        src = re.sub(r'""".*?"""', '', src, flags=re.S)
        src = re.sub(r"#.*", "", src)
        for i, l in enumerate(src.splitlines(), 1):
            if ".days <= 7" in l or ".days <= 3" in l:
                hard.append(f"{p.name}:{i}")
    assert not hard, "corte de risco hardcoded ainda em: " + ", ".join(hard)


check("RISCO_DIAS: constante unica (3 dias)", t_constante_unica)


def t_fronteiras():
    """A regra nos dias exatos: -1 e 0 e 3 e 4 dias."""
    from gui.components.timeline.timeline_mapper import RISCO_DIAS
    from gui.views.project_360_qt import Project360Qt
    from services.project_service import ProjectService
    from models.entities import Project, Task
    from unittest import mock

    ps = ProjectService().get_all_active()
    v = Project360Qt(ps[0].id)
    hoje = datetime.date.today()

    def dias(d):
        return (hoje + datetime.timedelta(days=d)).isoformat()

    # projeto isolado: nenhuma tarefa, so o prazo do projeto
    def checar(dias_restantes, esperado):
        proj = Project(id=1, name="P", status="Ativo",
                       due_date=None if dias_restantes is None else dias(dias_restantes))
        v.project = proj
        with mock.patch.object(v.task_service, "get_tasks_by_project", return_value=[]):
            with mock.patch.object(v.task_service, "get_all_archived", return_value=[]):
                got = v._progress_color(10, 0)
        assert got == esperado, (
            f"prazo em {dias_restantes}d -> {got}, esperado {esperado}")

    checar(None, ACCENT_BLUE)      # sem prazo
    checar(30, ACCENT_BLUE)        # folgado
    checar(RISCO_DIAS + 1, ACCENT_BLUE)   # 4 dias -> azul
    checar(RISCO_DIAS, WARNING_ORANGE)    # 3 dias -> laranja (limite)
    checar(1, WARNING_ORANGE)      # amanha -> laranja
    checar(0, WARNING_ORANGE)      # hoje -> laranja
    checar(-1, ERROR_RED)          # VENCIDO -> vermelho (bug antigo: era laranja)
    checar(-10, ERROR_RED)         # muito vencido -> vermelho


check("fronteiras: 4=azul 3=laranja 0=laranja -1=vermelho", t_fronteiras)


def t_marco_nao_atrasa():
    """Marco (milestone) nao tem prazo final: nunca marca atraso."""
    from gui.views.project_360_qt import Project360Qt
    from services.project_service import ProjectService
    from models.entities import Task
    from unittest import mock

    ps = ProjectService().get_all_active()
    v = Project360Qt(ps[0].id)
    hoje = datetime.date.today()
    ontem = (hoje - datetime.timedelta(days=1)).isoformat()

    marco = Task(id=1, title="Marco", status="Pendente", due_date=ontem, is_milestone=True)
    normal = Task(id=2, title="Normal", status="Pendente", due_date=ontem, is_milestone=False)

    v.project.due_date = None
    with mock.patch.object(v.task_service, "get_tasks_by_project", return_value=[marco]):
        with mock.patch.object(v.task_service, "get_all_archived", return_value=[]):
            got = v._progress_color(10, 0)
    assert got == ACCENT_BLUE, f"marco vencido marcou {got}; marco nao tem prazo final"

    with mock.patch.object(v.task_service, "get_tasks_by_project", return_value=[marco, normal]):
        with mock.patch.object(v.task_service, "get_all_archived", return_value=[]):
            got = v._progress_color(10, 0)
    assert got == ERROR_RED, f"tarefa normal vencida deveria marcar vermelho, veio {got}"


check("marco vencido nao marca atraso; tarefa normal marca", t_marco_nao_atrasa)


def t_data_invalida_nao_quebra():
    from gui.views.project_360_qt import Project360Qt
    from services.project_service import ProjectService
    from models.entities import Project
    from unittest import mock

    ps = ProjectService().get_all_active()
    v = Project360Qt(ps[0].id)
    for bad in ["lixo", "31/12/2020", "", None, "2026-13-45"]:
        v.project = Project(id=1, name="P", status="Ativo", due_date=bad or None)
        with mock.patch.object(v.task_service, "get_tasks_by_project", return_value=[]):
            with mock.patch.object(v.task_service, "get_all_archived", return_value=[]):
                got = v._progress_color(10, 0)
        assert got in (ACCENT_BLUE, WARNING_ORANGE, ERROR_RED), f"data invalida {bad!r} -> {got}"


check("data invalida nao quebra nem pinta fora da paleta", t_data_invalida_nao_quebra)


def t_ordem_de_decisao():
    """A primeira regra que casar vence: verde tem prioridade sobre tudo."""
    from gui.views.project_360_qt import Project360Qt
    from services.project_service import ProjectService
    from models.entities import Project, Task
    from unittest import mock

    ps = ProjectService().get_all_active()
    v = Project360Qt(ps[0].id)
    hoje = datetime.date.today()
    ontem = (hoje - datetime.timedelta(days=1)).isoformat()

    # tudo concluído E com tarefa vencida: concluído ganha (a tarefa vencida
    # nao conta, porque esta Concluída)
    v.project = Project(id=1, name="P", status="Concluído", due_date=ontem)
    done = Task(id=1, title="A", status="Concluído", due_date=ontem)
    with mock.patch.object(v.task_service, "get_tasks_by_project", return_value=[done]):
        with mock.patch.object(v.task_service, "get_all_archived", return_value=[]):
            got = v._progress_color(1, 1)
    assert got == SUCCESS_GREEN, f"tudo concluido deveria ser verde, veio {got}"


check("ordem de decisao: concluido vence", t_ordem_de_decisao)

print("=" * 64)
for n in ok:
    print(f"  OK   {n}")
for n in fail:
    print(f"  FAIL {n}")
print("=" * 64)
print(f"{len(ok)} ok / {len(fail)} fail")
sys.exit(1 if fail else 0)