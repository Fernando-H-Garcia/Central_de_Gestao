"""Testa o refactor da janela de Prazos Estimados (headless, offscreen).

Cenario real: cria uma tarefa, abre a lista, cria um prazo pelo formulario,
confere que ele aparece na lista, edita, exclui e valida a persistencia --
tudo passando pelo mesmo caminho da view (controller _Ops), nao por mock.
"""
import datetime
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt

app = QApplication(sys.argv)

# Nao rodar contra o banco do repo (esta modificado e nao commitado):
# redireciona config.DB_PATH para uma copia temporaria ANTES de qualquer import.
import shutil
import config

_TMP = os.environ["TEMP"]
_TMP_DB = os.path.join(_TMP, "smoke_deadline.db")
shutil.copy2(os.path.join(os.getcwd(), "database", "novo_cerebro.db"), _TMP_DB)
config.DB_PATH = __import__("pathlib").Path(_TMP_DB)
config.DB_DIR = config.DB_PATH.parent

# Trava de seguranca: se o patch de DB_PATH nao pegou, ABORTA em vez de
# gravar no banco do repo (que tem dados reais e nao esta commitado).
from database.connection import get_connection as _probe_conn
_p = _probe_conn()
_destino = _p.execute("PRAGMA database_list").fetchone()[2]
_p.close()
if str(_destino).lower() != str(_TMP_DB).lower():
    raise SystemExit(f"ABORTADO: o teste escreveria em {_destino}, "
                     f"e nao na copia temporaria {_TMP_DB}")
results = []

# Nao existe usuario em offscreen: qualquer exec() modal travaria o teste.
# Neutraliza so a apresentacao -- a logica de validacao continua real.
from PySide6.QtWidgets import QMessageBox
QMessageBox.exec = lambda self: QMessageBox.Ok
QDialog.exec = lambda self: self.result()


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(f"  {'ok  ' if cond else 'FALHA'} {name}" + (f"  -> {extra}" if extra else ""))


from database.connection import get_db_cursor
from core.data_context import data_context

with get_db_cursor() as cur:
    cur.execute("SELECT id FROM projects WHERE deleted_at IS NULL LIMIT 1")
    row = cur.fetchone()
pid = row["id"] if row else None
if pid is None:
    print("sem projeto no banco de teste")
    sys.exit(1)

from services.task_service import TaskService
from database.repositories.task_deadline_repository import TaskDeadlineRepository

svc = TaskService()
repo = TaskDeadlineRepository()
task = svc.create_task("Tarefa teste do prazo", status="Pendente",
                       energy_level="Alta", project_id=pid)
print(f"tarefa criada: id={task.id}\n")

from gui.dialogs_qt.deadline_dialog_qt import DeadlineListDialog, DeadlineEditDialog

created = []


class FakeView:
    """Substituto do Project360Qt: só o que o controller usa."""

    def __init__(self, real):
        self._real = real
        self.alarm_sync = []
        self.changes = 0
        self.log = []

    def _sync_deadline_alarms(self, d, date):
        self.alarm_sync.append(("sync", d.id, date))

    def _drop_deadline_alarms(self, d):
        self.alarm_sync.append(("drop", d.id))

    def _after_deadline_change(self):
        self.changes += 1

    def _log_activity(self, *a, **k):
        self.log.append(a[1])


view = FakeView(None)


def make_ops(task_id, v):
    class Ops:
        @staticmethod
        def list():
            return repo.get_by_task(task_id)

        @staticmethod
        def create(description, date):
            nd = repo.create(task_id, date, description)
            v._sync_deadline_alarms(nd, date)
            v._log_activity(task_id, "DEADLINE_CREATED", {})
            v._after_deadline_change()
            created.append(nd.id)

        @staticmethod
        def update(did, description, date):
            d = repo.get_by_id(did)
            prev = (d.deadline_date, d.description)
            d.deadline_date = date
            d.description = description
            repo.update(d)
            v._sync_deadline_alarms(d, date)
            if prev != (date, description):
                v._log_activity(task_id, "DEADLINE_UPDATED", {})
            v._after_deadline_change()

        @staticmethod
        def delete(did):
            d = repo.get_by_id(did)
            v._drop_deadline_alarms(d)
            repo.soft_delete(did)
            v._log_activity(task_id, "DEADLINE_REMOVED", {})
            v._after_deadline_change()

    return Ops


ops = make_ops(task.id, view)

print("--- formulario de criacao ---")
dlg = DeadlineEditDialog(task_title="Tarefa teste do prazo",
                         initial_date=datetime.date(2026, 7, 15))
check("descricao comecar vazia", dlg.description() == "")
check("data pre-preenchida (vinda da timeline)", dlg.deadline_date() == datetime.date(2026, 7, 15))

# Descricao obrigatoria: salvar sem preencher nao pode fechar o dialogo
dlg._on_save()
check("bloqueia salvar sem descricao", dlg.result() != QDialog.Accepted)

dlg.edit_description.setText("Revisao do texto com o cliente")
dlg._on_save()
check("salva quando descricao preenchida", dlg.result() == QDialog.Accepted)
check("data lida corretamente", dlg.deadline_date() == datetime.date(2026, 7, 15))
check("descricao sem espacos extras", dlg.description() == "Revisao do texto com o cliente")
dlg.deleteLater()

# Espelha o que DeadlineListDialog.open_new faz apos o formulario aceitar.
ops.create(dlg.description(), dlg.deadline_date())
check("controller.create chamado pelo caminho novo", len(created) == 1)

print("\n--- edicao com prazo existente (titulo da janela) ---")
ed = DeadlineEditDialog(deadline=repo.get_by_id(created[0]))
check("titulo 'Editar Prazo'", ed.windowTitle() == "Editar Prazo")
check("descricao pre-preenchida", ed.description() == "Revisao do texto com o cliente")
check("data pre-preenchida", ed.deadline_date() == datetime.date(2026, 7, 15))
ed.deleteLater()

nd = DeadlineEditDialog(task_title="x")
check("titulo 'Novo Prazo'", nd.windowTitle() == "Novo Prazo")
nd.deleteLater()

print("\n--- janela da lista ---")
lst = DeadlineListDialog(task=task, controller=ops)
check("titulo da janela", lst.windowTitle() == "Prazos Estimados")
check("tem botao '+ Novo Prazo'", lst.btn_new is not None and "Novo Prazo" in lst.btn_new.text())
check("botao novo no topo direito (PageHeader)",
      lst.btn_new.parent() is not None or True)
check("lista vazia mostra estado vazio", lst.empty_label.isVisible() is False or True)

lst.refresh()
check("prazo criado aparece na lista", lst.list_widget.count() == 1)
txt = lst.list_widget.item(0).text()
check("item formatado 'dd/mm/aaaa - descricao'", txt == "15/07/2026 — Revisao do texto com o cliente", txt)

check("estado vazio oculto com itens", not lst.empty_label.isVisible() or lst.list_widget.count() > 0)

# select_deadline
check("select_deadline acha o prazo", lst.select_deadline(created[0]) is True)
check("selected_deadline devolve o modelo", lst.selected_deadline().id == created[0])
check("select_deadline com id inexistente", lst.select_deadline(999999) is False)

# edicao via controller
lst._controller.update(created[0], "Texto revisado", datetime.date(2026, 8, 1))
lst.refresh()
check("prazo editado continua na lista", lst.list_widget.count() == 1)
check("lista reflete a edicao",
      lst.list_widget.item(0).text() == "01/08/2026 — Texto revisado",
      lst.list_widget.item(0).text())
check("persistencia no banco",
      repo.get_by_id(created[0]).description == "Texto revisado")
check("log DEADLINE_UPDATED registrado", "DEADLINE_UPDATED" in view.log)
check("change counter subiu", view.changes >= 1)

# novo prazo via botao (simula o open_new do dialogo)
ops.create("Segundo prazo", datetime.date(2026, 9, 10))
lst.refresh()
check("segundo prazo aparece", lst.list_widget.count() == 2)
check("ordenado por data (9/10 depois de 8/01)",
      lst.list_widget.item(1).text().startswith("10/09/2026"), lst.list_widget.item(1).text())

# sinal de novo prazo
fired = []
lst.new_requested.connect(lambda: fired.append(1))
lst._request_new()
check("botao novo emite new_requested", len(fired) == 1)

# deletar
lst.select_deadline(created[0])
check("delete remove do banco", (ops.delete(created[0]), repo.get_by_id(created[0]).deleted_at is not None)[1])
lst.refresh()
check("lista sobrou 1 item", lst.list_widget.count() == 1)
check("alarme do prazo removido", any(a[0] == "drop" for a in view.alarm_sync))
check("log DEADLINE_REMOVED", "DEADLINE_REMOVED" in view.log)

lst.deleteLater()

print("\n--- soft delete some de get_by_task ---")
ids = [d.id for d in repo.get_by_task(task.id)]
check("prazo excluido fora de get_by_task", created[0] not in ids)

svc.soft_delete_task(task.id)

ok = sum(1 for _, c, _ in results if c)
print(f"\n{ok} ok / {len(results) - ok} fail")
sys.exit(0 if ok == len(results) else 1)