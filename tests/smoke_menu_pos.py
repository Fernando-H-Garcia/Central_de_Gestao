"""Verifica que o menu de contexto nasce exatamente sob o cursor.

O bug anterior: `_on_context_menu` passava `mapToGlobal(pos)` para o
`popup_at`, que JÁ faz o mapToGlobal -- a posicao era convertida duas
vezes e o menu abria deslocado. Aqui medimos a posicao real em que o
menu e展示了.
"""
import datetime
import os
import shutil
import sys

os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint

app = QApplication(sys.argv)
from gui.theme import GLOBAL_STYLE, LightBranchStyle
app.setStyleSheet(GLOBAL_STYLE)
app.setStyle(LightBranchStyle())

import config
_TMP = os.path.join(os.environ["TEMP"], "menu_pos.db")
shutil.copy2(os.path.join(os.getcwd(), "database", "novo_cerebro.db"), _TMP)
config.DB_PATH = __import__("pathlib").Path(_TMP)

# Trava de seguranca: se o patch de DB_PATH nao pegou, ABORTA em vez de
# gravar no banco do repo (que tem dados reais e nao esta commitado).
from database.connection import get_connection as _probe_conn
_p = _probe_conn()
_destino = _p.execute("PRAGMA database_list").fetchone()[2]
_p.close()
if str(_destino).lower() != str(_TMP).lower():
    raise SystemExit(f"ABORTADO: o teste escreveria em {_destino}, "
                     f"e nao na copia temporaria {_TMP}")
from database.connection import get_db_cursor
with get_db_cursor() as cur:
    cur.execute("SELECT id FROM projects WHERE deleted_at IS NULL LIMIT 1")
    pid = cur.fetchone()["id"]

from services.task_service import TaskService
from database.repositories.task_deadline_repository import TaskDeadlineRepository
svc, repo = TaskService(), TaskDeadlineRepository()
task = svc.create_task("Tarefa posicao menu", project_id=pid)
for i in range(4):
    repo.create(task.id, datetime.date(2026, 6, 10 + i), f"Prazo {i}")

from gui.dialogs_qt.deadline_dialog_qt import DeadlineListDialog


class Ops:
    list = staticmethod(lambda: repo.get_by_task(task.id))
    create = staticmethod(lambda d, dt: None)
    update = staticmethod(lambda *a: None)
    delete = staticmethod(lambda *a: None)


results = []


def check(nome, cond, extra=""):
    results.append((nome, bool(cond)))
    print(f"  {'ok  ' if cond else 'FALHA'} {nome}" + (f"  -> {extra}" if extra else ""))


lst = DeadlineListDialog(task=task, controller=Ops)
lst.show()
app.processEvents()

# Espia a posicao GLOBAL em que o popup abriria, sem exibir.
capturado = {}
from gui.components.context_menu_qt import ContextMenuQt
_real = ContextMenuQt.popup_at


def spy(self, widget, pos):
    # reproduz o que popup_at faz, mas guarda em vez de exibir
    capturado["viewport_pos"] = QPoint(pos)
    capturado["global_pos"] = widget.viewport().mapToGlobal(pos)
    return None


ContextMenuQt.popup_at = spy

item = lst.list_widget.item(2)
rect = lst.list_widget.visualItemRect(item)
pos = rect.center()
esperado = lst.list_widget.viewport().mapToGlobal(pos)

lst._on_context_menu(pos)

check("popup_at chamado com pos do viewport (nao global)",
      capturado["viewport_pos"] == QPoint(pos),
      f"recebido={capturado['viewport_pos'].x()},{capturado['viewport_pos'].y()} "
      f"local={pos.x()},{pos.y()}")
check("posicao global calculada == posicao do cursor",
      capturado["global_pos"] == esperado,
      f"menu em {capturado['global_pos'].x()},{capturado['global_pos'].y()} "
      f"cursor em {esperado.x()},{esperado.y()}")
check("distancia do cursor = 0 px",
      capturado["global_pos"] == esperado)

# Confere em varias linhas: o erro de mapeamento duplo cresce com a posicao

deltas = []
for row in range(lst.list_widget.count()):
    p = lst.list_widget.visualItemRect(lst.list_widget.item(row)).center()
    exp = lst.list_widget.viewport().mapToGlobal(p)
    lst._on_context_menu(p)
    got = capturado["global_pos"]
    deltas.append(got.x()-exp.x()); deltas.append(got.y()-exp.y()); print(f"    linha {row}: pos={p.x()},{p.y()} esperado={exp.x()},{exp.y()} obtido={got.x()},{got.y()} delta={got.x()-exp.x()},{got.y()-exp.y()} item_at={lst.list_widget.itemAt(p) is not None}")


for row in range(lst.list_widget.count()):
    p = lst.list_widget.visualItemRect(lst.list_widget.item(row)).center()
    exp = lst.list_widget.viewport().mapToGlobal(p)
    lst._on_context_menu(p)
    if capturado["global_pos"] != exp:
        todos_ok = False
svc.soft_delete_task(task.id)
check("posicao correta em todas as linhas (delta 0,0)", all(d == 0 for d in deltas), f"deltas={deltas}")
ok = sum(1 for _, c in results if c)
print(f"\n{ok} ok / {len(results) - ok} fail")
sys.exit(0 if ok == len(results) else 1)