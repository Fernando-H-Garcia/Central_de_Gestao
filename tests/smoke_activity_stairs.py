"""Escadinha continua no Resumo das Atividades (headless, offscreen).

Regra: titulo(1 passo) -> registro(2) -> subtarefa(3) -> registro-sub(4)...
O registro do pai NAO pode ficar na mesma margem do cabecalho da filha:
as filhas vao dentro de um wrapper com +INDENT_STEP a esquerda, e os
registros ficam diretos no corpo da propria tarefa.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QWidget

app = QApplication(sys.argv)

import shutil
import config

_TMP = os.environ["TEMP"]
_TMP_DB = os.path.join(_TMP, "smoke_activity_stairs.db")
shutil.copy2(os.path.join(os.getcwd(), "database", "novo_cerebro.db"), _TMP_DB)
config.DB_PATH = __import__("pathlib").Path(_TMP_DB)
config.DB_DIR = config.DB_PATH.parent

from database.connection import get_connection as _probe_conn
_p = _probe_conn()
_destino = _p.execute("PRAGMA database_list").fetchone()[2]
_p.close()
if str(_destino).lower() != str(_TMP_DB).lower():
    raise SystemExit(f"ABORTADO: o teste escreveria em {_destino}, "
                     f"e nao na copia temporaria {_TMP_DB}")

results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(f"  {'ok  ' if cond else 'FALHA'} {name}" + (f"  -> {extra}" if extra else ""))


from services.project_service import ProjectService
from services.task_service import TaskService
from gui.views.activity_summary_qt import ActivitySummaryQt
from gui.components.collapsible_section_qt import CollapsibleSection

STEP = CollapsibleSection.INDENT_STEP

proj = ProjectService().create_project(name="Projeto Escada Stairs")
t1 = TaskService().create_task(title="Tarefa 1", project_id=proj.id)
s1 = TaskService().create_task(title="Sub da T1", project_id=proj.id, parent_task_id=t1.id)
for t, txt in [(t1, "reg t1"), (s1, "reg sub")]:
    TaskService().add_manual_activity(t.id, txt)

view = ActivitySummaryQt()
view.resize(900, 600)
view.show()
view.cmb_project.setCurrentIndex(view.cmb_project.findData(proj.id))
view._buscar()
app.processEvents()

secs = view.findChildren(CollapsibleSection)
by_task = {}
proj_sec = None
for s in secs:
    tid = s.header.property("task_id")
    pid = s.header.property("project_id")
    if pid and int(pid) == proj.id:
        proj_sec = s
    if tid:
        by_task[s.header.text().split("  ")[-1].replace("└─ ", "")] = s

check("projeto renderizado", proj_sec is not None)
check("tarefas renderizadas", "Tarefa 1" in by_task and "Sub da T1" in by_task,
      f"achadas={sorted(by_task)}")

def direct_widgets(layout):
    out = []
    for i in range(layout.count()):
        w = layout.itemAt(i).widget()
        if w is not None:
            out.append(w)
    return out

sec_t1 = by_task.get("Tarefa 1")
if sec_t1 is None:
    check("corpo da Tarefa 1 tem registros + wrapper (PULADO)", False, "secao nao achada")
else:
    kids = direct_widgets(sec_t1.body_layout)
    logs = [w for w in kids if isinstance(w, QLabel)]
    wraps = [w for w in kids
             if type(w) is QWidget and w.layout() is not None]
    direct_subs = [w for w in kids if isinstance(w, CollapsibleSection)]
    check("registros ficam diretos no corpo da tarefa", len(logs) >= 1,
          f"labels={len(logs)}")
    check("nenhuma filha direta no corpo (vão no wrapper)", len(direct_subs) == 0,
          f"diretas={len(direct_subs)}")
    check("existe um wrapper para as filhas", len(wraps) == 1,
          f"wrappers={len(wraps)}")
    if wraps:
        left = wraps[0].layout().contentsMargins().left()
        check("wrapper adiciona +1 passo", left == STEP, f"left={left}")
        inner = direct_widgets(wraps[0].layout())
        check("subtarefa esta dentro do wrapper",
              any(isinstance(w, CollapsibleSection) for w in inner),
              f"inner={[type(w).__name__ for w in inner]}")
        # o registro do pai e o cabecalho da filha em offsets distintos:
        # filho = corpo(STEP) + wrapper(STEP) alem do titulo da tarefa
        check("degraus titulo(0) < registro(STEP) < filha(2*STEP)",
              sec_t1.body_layout.contentsMargins().left() == STEP
              and left == STEP)

ok = sum(1 for _, c, _ in results if c)
fail = len(results) - ok
print(f"{ok} ok / {fail} fail")
sys.exit(1 if fail else 0)
