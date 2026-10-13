"""Regra do pre-preenchimento da data do prazo.

Ordem (AGENTS.md): prazo existente > data sob o mouse (timeline) > hoje.

Este teste exercita os TRES caminhos de entrada de
`Project360Qt._edit_estimated_deadline` e verifica qual dialogo aparece e
com qual data -- sem depender de clicar na tela: os `exec()` sao
interceptados para registrar qual formulario foi aberto.
"""
import datetime
import os
import shutil
import sys

os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
from gui.theme import GLOBAL_STYLE, LightBranchStyle
app.setStyleSheet(GLOBAL_STYLE)
app.setStyle(LightBranchStyle())

import config
_TMP = os.path.join(os.environ["TEMP"], "prazo_prefill.db")
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
task = svc.create_task("Tarefa prefill", project_id=pid)

from gui.dialogs_qt import deadline_dialog_qt as dd
from PySide6.QtWidgets import QDialog

results = []


def check(nome, cond, extra=""):
    results.append((nome, bool(cond)))
    print(f"  {'ok  ' if cond else 'FALHA'} {nome}" + (f"  -> {extra}" if extra else ""))


# Intercepta exec() de ambos os formularios para saber qual abriu e com que data.
abertos = []


def instrumentar_edit(cancelar=True):
    orig = dd.DeadlineEditDialog.exec

    def spy(self):
        abertos.append({
            "tipo": "editar" if self._deadline is not None else "novo",
            "data": self.deadline_date(),
            "descricao": self.description(),
            "tem_task_title": bool(self.windowTitle()),
        })
        return QDialog.Rejected if cancelar else QDialog.Accepted
    dd.DeadlineEditDialog.exec = spy
    return orig


def instrumentar_lista():
    orig = dd.DeadlineListDialog.exec

    def spy(self):
        abertos.append({"tipo": "lista"})
        return QDialog.Rejected
    dd.DeadlineListDialog.exec = spy
    return orig


HOJE = datetime.date.today()
MOUSE = datetime.date(2027, 3, 17)

from PySide6.QtWidgets import QWidget
from gui.views.project_360_qt import Project360Qt


class Stub(QWidget):
    """QWidget real (pai legitimo dos dialogos) com os metodos de que o
    roteamento precisa. A LOGICA de roteamento e a real: os metodos de
    Project360Qt sao vinculados aqui."""

    def __init__(self):
        super().__init__()
        self.task_service = svc
        self.loads = 0

    def _resolve_timeline_task(self, ref):
        return task if ref is None else svc.task_repo.get_by_id(ref)

    def _deadline_repo(self):
        return repo

    def _sync_deadline_alarms(self, d, dt):
        pass

    def _drop_deadline_alarms(self, d):
        pass

    def load_data(self):
        self.loads += 1


# logica real, sem construir a tela inteira
Stub._edit_estimated_deadline = Project360Qt._edit_estimated_deadline
Stub._edit_estimated_deadline_at = Project360Qt._edit_estimated_deadline_at
Stub._after_deadline_change = Project360Qt._after_deadline_change
Stub._drop_deadline_alarms = Project360Qt._drop_deadline_alarms

view = Stub()

print("=== 1. Timeline: menu 'Prazo Estimado' com data sob o mouse ===")
e_orig, l_orig = instrumentar_edit(), instrumentar_lista()
view._edit_estimated_deadline_at(task.id, MOUSE)
check("abriu o formulario de criacao (nao a lista)",
      abertos and abertos[-1]["tipo"] == "novo", abertos[-1]["tipo"] if abertos else "nada")
check("data pre-preenchida = data sob o mouse",
      abertos[-1]["data"] == MOUSE, f"{abertos[-1]['data']} != {MOUSE}")
dd.DeadlineEditDialog.exec = e_orig

print("\n=== 2. Timeline: clique FORA da area da timeline (sem data sob o mouse) ===")
e_orig, l_orig = instrumentar_edit(), instrumentar_lista()
view._edit_estimated_deadline_at(task.id, None)
check("ainda abre o formulario de criacao (nao a lista)",
      abertos[-1]["tipo"] == "novo", abertos[-1]["tipo"])
check("data pre-preenchida = hoje", abertos[-1]["data"] == HOJE,
      f"{abertos[-1]['data']} != {HOJE}")
dd.DeadlineEditDialog.exec = e_orig

print("\n=== 3. Menu do marcador: editar prazo existente ===")
d = repo.create(task.id, datetime.date(2026, 5, 4), "Prazo da analise")
e_orig, l_orig = instrumentar_edit(), instrumentar_lista()
view._edit_estimated_deadline(task.id, deadline_id=d.id)
check("abriu edicao (nao criacao, nao lista)", abertos[-1]["tipo"] == "editar", abertos[-1]["tipo"])
check("data = data do prazo, NAO hoje nem mouse",
      abertos[-1]["data"] == datetime.date(2026, 5, 4), str(abertos[-1]["data"]))
check("descricao pre-preenchida", abertos[-1]["descricao"] == "Prazo da analise")
dd.DeadlineEditDialog.exec = e_orig

print("\n=== 4. Prioridade: prazo existente vence a data sob o mouse ===")
e_orig = instrumentar_edit()
view._edit_estimated_deadline(task.id, deadline_id=d.id, initial_date=MOUSE)
check("prazo existente tem prioridade", abertos[-1]["data"] == datetime.date(2026, 5, 4),
      str(abertos[-1]["data"]))
dd.DeadlineEditDialog.exec = e_orig

print("\n=== 5. Botao da tela da tarefa (sem parametros) abre a LISTA ===")
e_orig, l_orig = instrumentar_edit(), instrumentar_lista()
view._edit_estimated_deadline(task.id)
check("abriu a lista", abertos[-1]["tipo"] == "lista", abertos[-1]["tipo"])
dd.DeadlineListDialog.exec = l_orig
dd.DeadlineEditDialog.exec = e_orig

print("\n=== 6. Salvando o formulario de criacao realmente persiste ===")
criados = []


def spy_exec_aceita(self):
    abertos.append({"tipo": "novo", "data": self.deadline_date(),
                    "descricao": self.description()})
    return QDialog.Accepted


dd.DeadlineEditDialog.exec = spy_exec_aceita
view._edit_estimated_deadline_at(task.id, MOUSE)
antes = len(repo.get_by_task(task.id))
novo = repo.get_by_task(task.id)
check("prazo criado com a data do mouse", novo[-1].deadline_date == MOUSE, str(novo[-1].deadline_date))
check("prazo criado com a descricao", novo[-1].description == "", "(vazio, pois nao digitamos)")
check("load_data chamado (refresh da view)", view.loads >= 1)
dd.DeadlineEditDialog.exec = e_orig

print("\n=== 7. REGRESSAO: fechar a janela NAO pode abrir o formulario sozinho ===")
# Bug reportado: no caminho da timeline, a versao anterior abria a LISTA e so
# depois do exec() (ou seja, ao fechar a lista) aparecia o "Novo Prazo".
e_orig, l_orig = instrumentar_edit(), instrumentar_lista()
abertos.clear()
view._edit_estimated_deadline_at(task.id, MOUSE)
# "fechar" = os dois exec() ja retornaram; nada mais pode abrir depois
check("so 1 dialogo aberto no caminho da timeline", len(abertos) == 1,
      f"{len(abertos)}: {[a['tipo'] for a in abertos]}")
check("foi o formulario direto, sem a lista no meio",
      [a["tipo"] for a in abertos] == ["novo"], str([a["tipo"] for a in abertos]))
dd.DeadlineEditDialog.exec = e_orig
dd.DeadlineListDialog.exec = l_orig

abertos.clear()
e_orig, l_orig = instrumentar_edit(), instrumentar_lista()
view._edit_estimated_deadline(task.id)
check("fechar a lista nao abre formulario depois", [a["tipo"] for a in abertos] == ["lista"],
      str([a["tipo"] for a in abertos]))
dd.DeadlineEditDialog.exec = e_orig
dd.DeadlineListDialog.exec = l_orig

repo.soft_delete(d.id)
svc.soft_delete_task(task.id)
ok = sum(1 for _, c in results if c)
print(f"\n{ok} ok / {len(results) - ok} fail")
sys.exit(0 if ok == len(results) else 1)