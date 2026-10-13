# Testes

## Como rodar

Cada suíte é um script independente, executado com `python -B`:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -B tests\smoke_deadline.py
```

Saída no formato `N ok / M fail`. O script retorna `exit 1` se houver falha.

`-B` desliga a escrita de `.pyc` — evita o caso de rodar código antigo por
bytecode em cache depois de editar os fontes.

## Suítes de Prazos Estimados

| Suíte | Checks | Cobre |
|---|---|---|
| `smoke_deadline.py` | 34 | Formulário e lista: criar, editar, excluir, persistir, alarmes, atividade |
| `smoke_menu_pos.py` | 4 | Menu de contexto nasce exatamente sob o cursor |
| `smoke_prefill.py` | 15 | Regra da data: prazo existente > data sob o mouse > hoje |
| `smoke_gantt_prazo.py` | 12 | Duplo clique vs botão direito no marcador da timeline |

## Suítes de Design System (Parte 1)

`smoke_1a`, `smoke_1b`, `smoke_1c`, `smoke_card_regressao`, `smoke_1d`,
`smoke_1e`, `smoke_risco`, `smoke_1f`, `smoke_perigo`, `smoke_header`,
`smoke_1g`.

Essas são análise estática (AST sobre o código-fonte), não executam a UI.

**Total: 15 suítes.**

> Essas suítes vivem em `tests/` no repositório. Se encontrar versões só em
> pasta temporária, elas não foram salvas ainda.

---

## Regras que os testes com banco devem seguir

Este projeto já perdeu dados de desenvolvimento para testes mal isolados.
Três regras obrigatórias:

### 1. Redirecionar `config.DB_PATH` antes de qualquer import

`config.DB_PATH` resolve para a raiz do repositório quando roda do
código-fonte. Sem redirecionamento, o teste grava no banco de desenvolvimento.

```python
import shutil, config
from pathlib import Path

_TMP_DB = Path(os.environ["TEMP"]) / "meu_teste.db"
shutil.copy2(Path("database/novo_cerebro.db"), _TMP_DB)
config.DB_PATH = _TMP_DB
config.DB_DIR = _TMP_DB.parent

# só agora importar o que acessa o banco
from database.connection import get_db_cursor
```

### 2. Instalar trava de segurança

Se o patch não pegar, o teste **aborta** em vez de corromper dados reais:

```python
from database.connection import get_connection
_probe = get_connection()
_destino = _probe.execute("PRAGMA database_list").fetchone()[2]
_probe.close()
if str(_destino).lower() != str(_TMP_DB).lower():
    raise SystemExit(f"ABORTADO: o teste escreveria em {_destino}")
```

Vale testar a trava invertendo o patch de propósito, para confirmar que ela
dispara.

### 3. Verificar o hash do banco depois

```powershell
(Get-FileHash database\novo_cerebro.db -Algorithm SHA256).Hash
```

Se mudou, restaure do backup antes de continuar.

---

## Modais em modo headless

Não existe usuário em modo automático: qualquer `exec()` modal trava o
teste indefinidamente. Neutralize **só a apresentação**, nunca a lógica:

```python
QMessageBox.exec = lambda self: QMessageBox.Ok
```

Com isso o caminho de validação continua sendo exercitado de verdade (a
validação roda, o diálogo é apenas não exibido).

## O que ainda não é testado

- A UI real em execução (screenshots são renderizados com a plataforma
  Windows, não `offscreen`, porque `offscreen` não tem fontes e o texto sai
  como tofu)
- Instalador em máquina limpa
- Instalação real (o EXE foi executado a partir de `build/dist`, não instalado)
- Sincronização de dados entre máquinas (não existe; ver
  [ADR-001](adr/ADR-001-SQLite.md))

## Smoke test do build

Além das suítes, o build tem o próprio smoke test:

```powershell
.\venv_build\Scripts\python.exe scripts\ops\control_panel.py test
```

E a validação mais forte de todas: **executar o EXE** e ler o `boot.log`.
Ver [`Release.md`](Release.md), Fase 3.