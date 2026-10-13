# Release

Procedimento oficial de build, validação, publicação e rollback.
Consolida o que estava espalhado entre `docs/engineering/23-Release.md`,
`docs/release/` e `docs/releasemanagement/`.

> Verificado em **2026-10-13**, com build e instalador gerados de fato
> (EXE 46,1 MB · instalador 70,1 MB · EXE executado e pintado).

## Ferramentas

| Ferramenta | Uso |
|---|---|
| `scripts/ops/control_panel.py` | **Ponto de entrada único** — é o que se chama |
| `scripts/core/engine.py` | Implementa as operações (build, test, release) |
| `scripts/build/build_release.py` | Executado pelo engine |
| `scripts/build/version.py` | Fonte única da versão (`VERSION`, `VERSION_SHORT`) |
| `scripts/guards/` | Regras constitucionais e checagens |
| `scripts/tests/` | Smoke test, validação de instalador, health check |

Comandos:

```powershell
.\venv_build\Scripts\python.exe scripts\ops\control_panel.py build            # só o EXE
.\venv_build\Scripts\python.exe scripts\ops\control_panel.py build --release  # + instalador
.\venv_build\Scripts\python.exe scripts\ops\control_panel.py test             # smoke test
.\venv_build\Scripts\python.exe scripts\ops\control_panel.py rollback <tag>   # rollback
```

**Regra:** nenhum build manual, nenhum PyInstaller chamado direto.
Sempre via `control_panel.py`. Os scripts soltos ainda funcionam, mas
estão deprecados (ver [`DEPRECATION.md`](DEPRECATION.md)).

Procedimento de build detalhado em [`BUILD.md`](BUILD.md).

---

## Fase 1 — Preparação

### Ambiente
- [ ] Python **3.11.5** — `.\venv_build\Scripts\python.exe --version`
- [ ] PySide6 6.6.3.1 — `python -c "import PySide6; print(PySide6.__version__)"`
- [ ] PyInstaller 6.21.0 — `python -c "import PyInstaller; print(PyInstaller.__version__)"`
- [ ] Inno Setup 6 em `C:\Program Files (x86)\Inno Setup 6\`
- [ ] `VC_redist.x64.exe` na raiz (opcional, mas recomendado)

> ⚠️ Ignore o aviso `[AVISO] Versao Python: 3.11.5 (esperado 3.12)`: o valor
> esperado no script está invertido. Python 3.12 **quebra** o build.

### Banco de dados
- [ ] Backup do banco do repositório + SHA-256 anotado
- [ ] Confirmar que o build **não mexe** no banco do repositório

> `build_release.py` não altera `database/novo_cerebro.db` (verificado).
> A troca por um seed limpo é passo **manual** e opcional — só é necessária
> se você for publicar e não quiser embutir dados de desenvolvimento.
> Se fizer, use o procedimento de seed limpo em [`BUILD.md`](BUILD.md) e
> **restaure o banco ao final**.

### Código
- [ ] Testes passando: `python -B tests\smoke_<assunto>.py`
- [ ] Banco de desenvolvimento íntegro: SHA-256 igual ao anotado

---

## Fase 2 — Build

- [ ] `control_panel.py build --release` executa sem erros
- [ ] Reporte diz **"Single EXE (onefile) - 1 arquivo"**
- [ ] `build\dist\CentralDeGestao.exe` existe, **~46 MB**
- [ ] `build\CentralDeGestao_Installer.exe` gerado, **~70 MB**
- [ ] `build\build_report.txt` e `build\build.hash` gravados
- [ ] Nenhum warning de hidden import

> 🚨 **Se o `.exe` tiver poucos MB, regredi para one-folder.** O sintoma é
> um `COLLECT` de volta no spec. O build ainda passa, silenciosamente.
> Ver [ADR-011](adr/ADR-011-OneFile.md).

---

## Fase 3 — Validação

Compilar **não** é validar. O build pode passar e o app não funcionar.

### Executar de verdade
- [ ] `Start-Process build\dist\CentralDeGestao.exe`
- [ ] Processo vivo após ~25 s
- [ ] `boot.log` mostra `MainWindow showEvent isVisible=True`
- [ ] `boot.log` mostra **`primeiro paint recebido`**
- [ ] `app_errors.log` **sem** `ERROR`/`Traceback` na data de hoje

> Erros antigos no log **não** contam. Confira a data: o log guarda histórico.

### Fluxo crítico
- [ ] Sidebar navega entre todas as telas
- [ ] Projetos: criar, editar, arquivar, restaurar
- [ ] Tarefas: criar, editar, concluir; subtarefas reordenáveis por drag
- [ ] Planning: barra arrastável, zoom, "Ir para hoje", prazos estimados
- [ ] Prazos: criar, editar, excluir; `+ Novo Prazo` e menu de contexto
- [ ] Wiki: editar, salvar, links `[[` e `{{` clicáveis
- [ ] Agenda: eventos e alarmes disparam
- [ ] Resumo de Atividades: logs agrupados por projeto/tarefa

### Instalador
- [ ] Instalador roda em Windows sem Python
- [ ] Instala em `C:\Program Files\Central de Gestão`
- [ ] Dados do usuário em `%LOCALAPPDATA%\CentralGestao\`
- [ ] Desinstalação remove o programa e **preserva** os dados

---

## Fase 4 — Publicação

- [ ] Versão conferida em `scripts/build/version.py`
- [ ] `CHANGELOG.md` atualizado
- [ ] Commit em branch, PR para `main` (sem commit direto na `main`)
- [ ] Tag: `git tag -a v0.x.y -m "Release v0.x.y"`
- [ ] Release no GitHub com o instalador anexado

Branch atual de trabalho: `feature/design-system-refactor`.

---

## Rollback

Se a validação falhar:

1. **Decidir a causa**: é código ou build?
2. **Código** → corrigir em branch, retestar, rebuildar.
3. **Build** → ajustar spec/scripts e rebuildar.
4. **Dados corrompidos** → restaurar o backup:
   ```powershell
   Copy-Item backups\pre_build.db database\novo_cerebro.db -Force
   Remove-Item database\novo_cerebro.db-wal,database\novo_cerebro.db-shm -ErrorAction SilentlyContinue
   ```
5. **Nunca** liberar com checklist incompleto.

Verificação de integridade após restaurar:

```powershell
python -B -c "import sqlite3; print(sqlite3.connect('database/novo_cerebro.db').execute('PRAGMA integrity_check').fetchone()[0])"
```

---

## Golden Release

O conceito era uma tag `golden-release` estável para fallback automático.
**Não está implementado** e as tags do repositório estão vazias. Se for
adotar, documente aqui quem promove e em que condições — não deixe a tag
morrer sem dono.

## Estado atual do release

| Campo | Valor |
|---|---|
| Versão | **0.8.1** (`VERSION_SHORT` = 0.8) |
| Build validado | 2026-10-13 |
| Artefatos | EXE 46,1 MB · instalador 70,1 MB |
| Validação | EXE executado, pintou, 0 erros no dia |
| Instalado em máquina limpa | **não** (pendente) |