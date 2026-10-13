# Deprecation Tracker

Funcionalidades, scripts e práticas em desuso.

---

## Em desuso

| # | Item | Tipo | Status | Desde | Previsão | Substituído por |
|---|------|------|--------|-------|----------|-----------------|
| 1 | Scripts de `scripts/build/` chamados diretamente | Script | `DEPRECATED` | v0.8.0 | v1.0.0 | `scripts/core/engine.py` via `scripts/ops/control_panel.py` |
| 2 | Scripts de `scripts/release/` chamados diretamente | Script | `DEPRECATED` | v0.8.0 | v1.0.0 | `scripts/core/engine.py` via `scripts/ops/control_panel.py` |
| 3 | Scripts de `scripts/tests/` chamados diretamente | Script | `DEPRECATED` | v0.8.0 | v1.0.0 | `scripts/core/engine.py` via `scripts/ops/control_panel.py` |
| 4 | Lógica de build fora de `scripts/core/engine.py` | Arquitetura | `DEPRECATED` | v0.8.0 | v1.0.0 | `scripts/core/engine.py` |
| 5 | `scripts/build/templates/cleanup_dlls.py` | Script | **ÓRFÃO** | — | — | Nada (não é executado) |

### Sobre o item 5
`cleanup_dlls.py` era usado no modo **one-folder** para remover DLLs
`api-ms-win-*` duplicadas. Com a mudança para **one-file** (ver
[ADR-011](adr/ADR-011-OneFile.md)) ele deixou de ser necessário — e hoje
**não é executado** pelo `build_release.py`. Sobrou como template. Mantido
por ora caso o build volte a one-folder; remover de vez se confirmar que não.

## Removidos

| # | Item | Removido em | Motivo | Substituído por |
|---|------|--------------|--------|-----------------|
| 1 | `gui/views/tasks_qt.py` | 2026-10 | Código morto (~484 KB) | `DragDropTreeWidget` em `gui/components/drag_drop_tree_qt.py` |
| 2 | `gui/components/timeline/timeline_canvas.py` | 2026-10 | Substituído pelo desenho no `GanttTree` | `gui/components/timeline/gantt_tree_qt.py` |
| 3 | `dist/` na raiz (209 MB) | 2026-10 | Resíduo de build one-folder antigo | `build/dist/` |
| 4 | `plugins/` | 2026-10 | Diretório vazio, nunca usado | — |
| 5 | `docs/engineering/`, `docs/release/`, `docs/releasemanagement/` | 2026-10 | 43 arquivos finos/duplicados e com fatos errados | Docs consolidados em `docs/` |
| 6 | `docs/images/` | 2026-10 | Só continha `.gitkeep` | — |

## Em observação

| # | Item | Motivo |
|---|------|--------|
| 1 | Aviso de versão do Python em `build_release.py` | Diz "esperado 3.12"; o correto é 3.11. Não atrapalha o build, mas induz a erro. |
| 2 | `core/snapshot_worker.py` | Nunca iniciado; `get_snapshot()` devolve vazio e os getters caem no repositório. Se alguém iniciar, views passam a ler dado velho. Ver [ADR-009](adr/ADR-009-EventBus.md). |
| 3 | `gui/views/notes_qt.py` (`NotesQt`) | Nunca instanciada. Código morto não detectado pela limpeza. |
| 4 | Golden Release | Conceito documentado, sem implementação e sem tag. Ver [`Release.md`](Release.md). |

## Regras

1. `DEPRECATED` ainda funciona, mas deveria emitir aviso.
2. `REMOVED` saiu do repositório.
3. Depreciação dura no mínimo um minor bump.
4. Remoção só em major bump.
5. Ao remover um item, registre o substituto aqui — um item deletado sem
   substituto viraArmadilha de documentação.