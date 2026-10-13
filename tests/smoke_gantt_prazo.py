"""Duplo clique no marcador vs botao direito no marcador.

Regras:
  - duplo clique no marcador (bandeirinha) -> FORMULARIO de edicao daquele prazo
  - botao direito no marcador -> menu com "Editar Prazos" -> LISTA da tarefa

O teste instancia o GanttTree de verdade, monta um item com prazo, e
dispara os dois eventos de mouse nas coordenadas do marcador.
"""
import datetime
import os
import shutil
import sys

os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

app = QApplication(sys.argv)
from gui.theme import GLOBAL_STYLE, LightBranchStyle
app.setStyleSheet(GLOBAL_STYLE)
app.setStyle(LightBranchStyle())

import config
_TMP = os.path.join(os.environ["TEMP"], "prazo_gantt.db")
shutil.copy2(os.path.join(os.getcwd(), "database", "novo_cerebro.db"), _TMP)
config.DB_PATH = __import__("pathlib").Path(_TMP)

# Trava de seguranca
from database.connection import get_connection as _probe_conn
_p = _probe_conn()
_destino = _p.execute("PRAGMA database_list").fetchone()[2]
_p.close()
if str(_destino).lower() != str(_TMP).lower():
    raise SystemExit(f"ABORTADO: escreveria em {_destino}")

from database.connection import get_db_cursor
with get_db_cursor() as cur:
    cur.execute("SELECT id FROM projects WHERE deleted_at IS NULL LIMIT 1")
    pid = cur.fetchone()["id"]

from services.task_service import TaskService
from database.repositories.task_deadline_repository import TaskDeadlineRepository
svc, repo = TaskService(), TaskDeadlineRepository()
task = svc.create_task("Tarefa gantt prazo", project_id=pid)
d1 = repo.create(task.id, datetime.date(2026, 8, 10), "Prazo um")
d2 = repo.create(task.id, datetime.date(2026, 9, 20), "Prazo dois")

results = []


def check(nome, cond, extra=""):
    results.append((nome, bool(cond)))
    print(f"  {'ok  ' if cond else 'FALHA'} {nome}" + (f"  -> {extra}" if extra else ""))


from gui.components.timeline.gantt_tree_qt import GanttTree
from gui.components.timeline.timeline_geometry import TimelineGeometry
from models.entities import TaskDeadline

# monta um item de timeline com um prazo estimado
geo = TimelineGeometry()
geo.anchor_date = datetime.date(2026, 8, 1)   # marca cai em x~90 (na tela)
geo.pixels_per_day = 10.0

deadlines = [TaskDeadline(id=d1.id, task_id=task.id,
                          deadline_date=d1.deadline_date,
                          description=d1.description)]
t_item = _mk_item = None

from gui.components.timeline.timeline_models import TimelineItem, DeadlineMark

t_item = TimelineItem(
    id=task.id, parent_id=None, title=task.title, level=0,
    is_parent=False, is_expanded=True,
    manual_start=datetime.date(2026, 8, 1), manual_end=datetime.date(2026, 9, 30),
    start=datetime.date(2026, 8, 1), end=datetime.date(2026, 9, 30),
    status=task.status, is_milestone=False, raw_task=task,
    deadlines=[DeadlineMark(id=d1.id, task_id=task.id,
                            date=d1.deadline_date, desc=d1.description)],
)

tree = GanttTree(geo)
tree.resize(1200, 200)
tree._scroll_y = 0
tree._offset_x = 0

# adiciona a linha
from PySide6.QtWidgets import QTreeWidgetItem
row = QTreeWidgetItem(tree, ["Tarefa gantt prazo", "resumo"])
row.setData(0, Qt.UserRole, t_item)
# row height vem do ROW_HEIGHT do widget
tree.show()
app.processEvents()

# localiza o marcador na tela
# _deadline_at devolve (mark, x) -- nao um retangulo
procura_x = 20
achou = False
for x in range(20, 1150):
    hit, hx = tree._deadline_at(QPoint(x, 15))
    if hit is not None:
        dl_item, rect = hit, hx
        procura_x = x
        achou = True
        break
check("marcador do prazo encontrado na timeline", achou, f"x={procura_x}")

if not achou:
    print("\nmarcador nao localizado; abortando")
    sys.exit(1)

print("\n=== 1. DUPLO CLIQUE no marcador -> formulario de edicao ===")
vistos = {"edit": None, "lista": None}
tree.edit_deadline_requested.connect(
    lambda t, i: vistos.__setitem__("edit", i))
tree.deadline_list_requested.connect(lambda t: vistos.__setitem__("lista", t))

centro = QPoint(rect, 15)
ev = QMouseEvent(QMouseEvent.MouseButtonPress, QPointF(centro), QPointF(centro),
                 Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
tree.mouseDoubleClickEvent(ev)
check("duplo clique emitiu edit_deadline_requested", vistos["edit"] is not None)
check("com o id do prazo sob o cursor", vistos["edit"] == d1.id, str(vistos["edit"]))
check("NAO emitiu a lista", vistos["lista"] is None)

print("\n=== 2. BOTAO DIREITO no marcador -> 'Editar Prazos' ===")
from gui.components.context_menu_qt import ContextMenuQt
rotulos = {}
_orig = ContextMenuQt.popup


def spy_popup(self, global_pos):
    rotulos["itens"] = [a.text() for a in self.actions() if a.text()]
    return self.actions()[0]   # simula o clique na primeira acao
ContextMenuQt.popup = spy_popup

vistos["edit"] = None
vistos["lista"] = None
ev_r = QMouseEvent(QMouseEvent.MouseButtonPress, QPointF(centro), QPointF(centro),
                   Qt.RightButton, Qt.RightButton, Qt.NoModifier)
tree.contextMenuEvent(ev_r)

itens = rotulos.get("itens", [])
print(f"    menu: {itens}")
check("menu tem 'Editar Prazos'", any("Editar Prazos" in i for i in itens))
check("rotulo antigo 'Editar Prazo Estimado' saiu",
      not any("Editar Prazo Estimado" in i for i in itens))
check("menu mantem 'Excluir Prazo'", any("Excluir Prazo" in i for i in itens))
check("menu mantem 'Abrir Tarefa'", any("Abrir Tarefa" in i for i in itens))
check("'Editar Prazos' emitiu deadline_list_requested", vistos["lista"] is not None)
check("NAO emitiu edicao de prazo especifico", vistos["edit"] is None)
ContextMenuQt.popup = _orig

print("\n=== 3. Roteamento na view ===")
from gui.views.project_360_qt import Project360Qt
from PySide6.QtWidgets import QDialog

# _open_deadline_list deve abrir a LISTA (sem parametros -> lista)
import gui.dialogs_qt.deadline_dialog_qt as dd
abertos = []
_orig_list = dd.DeadlineListDialog.exec
_orig_form = dd.DeadlineEditDialog.exec
dd.DeadlineListDialog.exec = lambda self: (abertos.append("lista"), QDialog.Rejected)[1]
dd.DeadlineEditDialog.exec = lambda self: (abertos.append("formulario"), QDialog.Rejected)[1]

from PySide6.QtWidgets import QWidget
Stub = type("Stub", (QWidget,), {})
for nome in ("_resolve_timeline_task", "_deadline_repo", "_sync_deadline_alarms",
             "_drop_deadline_alarms", "load_data"):
    setattr(Stub, nome, (lambda *a, **k: None))
Stub._resolve_timeline_task = lambda self, ref: task if ref is None else svc.task_repo.get_by_id(ref)
Stub._deadline_repo = lambda self: repo
Stub.__init__ = lambda self: (QWidget.__init__(self), setattr(self, "task_service", svc))[-1]
Stub._edit_estimated_deadline = Project360Qt._edit_estimated_deadline
Stub._open_deadline_list = Project360Qt._open_deadline_list
Stub._after_deadline_change = Project360Qt._after_deadline_change
Stub._drop_deadline_alarms = Project360Qt._drop_deadline_alarms

view = Stub()
view._open_deadline_list(task.id)
check("menu 'Editar Prazos' abre a LISTA", abertos == ["lista"], str(abertos))

abertos.clear()
view._edit_estimated_deadline(task.id, deadline_id=d1.id)
check("duplo clique abre o FORMULARIO", abertos == ["formulario"], str(abertos))

dd.DeadlineListDialog.exec = _orig_list
dd.DeadlineEditDialog.exec = _orig_form

repo.soft_delete(d1.id)
repo.soft_delete(d2.id)
svc.soft_delete_task(task.id)
ok = sum(1 for _, c in results if c)
print(f"\n{ok} ok / {len(results) - ok} fail")
sys.exit(0 if ok == len(results) else 1)