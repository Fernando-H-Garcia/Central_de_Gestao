"""Filtro de projetos do Resumo das Atividades acompanha projetos novos.

Cenario real do bug: view criada uma vez (QStackedWidget), combo carregado
so no __init__ -> projeto criado depois nunca aparecia no filtro ate
reiniciar o app.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

import shutil
import config

_TMP = os.environ["TEMP"]
_TMP_DB = os.path.join(_TMP, "smoke_activity_projects.db")
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
from gui.views.activity_summary_qt import ActivitySummaryQt

view = ActivitySummaryQt()
view.show()  # visivel p/ _safe_load_data funcionar se preciso

# 1. combo inicial lista todos os ativos
ativos = ProjectService().get_all_active()
ids_combo = {view.cmb_project.itemData(i) for i in range(view.cmb_project.count())}
check("combo inicial contem todos os ativos",
      all(p.id in ids_combo for p in ativos),
      f"combo={sorted(ids_combo)} ativos={[p.id for p in ativos]}")

# 2. cria projeto novo DEPOIS da view existir; showEvent/_load_projects deve trazer
novo = ProjectService().create_project(name="Projeto Filtro Novo XYZ")
check("projeto criado", novo is not None and novo.id is not None, f"id={getattr(novo, 'id', None)}")

view.showEvent(None) if False else None  # showEvent real precisa de evento; chama _load_projects direto
# simula o que showEvent e _buscar fazem
view._load_projects()
ids_combo2 = {view.cmb_project.itemData(i) for i in range(view.cmb_project.count())}
check("projeto novo aparece no filtro sem reiniciar",
      novo.id in ids_combo2, f"id={novo.id} combo={sorted(ids_combo2)}")

# 3. preserva selecao ao recarregar
idx = view.cmb_project.findData(novo.id)
view.cmb_project.setCurrentIndex(idx)
view._load_projects()
check("recarga preserva selecao",
      view.cmb_project.currentData() == novo.id,
      f"current={view.cmb_project.currentData()}")

# 4. _buscar nao derruba o filtro nem a selecao
try:
    view._buscar()
    ids_combo3 = {view.cmb_project.itemData(i) for i in range(view.cmb_project.count())}
    check("_buscar mantem projeto novo no filtro",
          novo.id in ids_combo3, f"combo={sorted(ids_combo3)}")
except Exception as e:
    check("_buscar executa sem excecao", False, str(e))

ok = sum(1 for _, c, _ in results if c)
fail = len(results) - ok
print(f"{ok} ok / {fail} fail")
sys.exit(1 if fail else 0)
