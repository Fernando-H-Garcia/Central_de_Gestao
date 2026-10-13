# Arquitetura

Referência técnica da estrutura do Central de Gestão. Este documento
consolida visão geral, arquitetura em camadas, fluxo de inicialização,
banco de dados e arquitetura Qt.

> Números aqui foram verificados no código em **2026-10-13**.

## Visão geral

O Central de Gestão é um sistema **desktop** (sem servidor) para gerenciamento
de projetos, tarefas (com subtarefas), prazos estimados, alarmes, eventos,
ideias, notas, wiki e resumo de atividades.

## Camadas

```
GUI (PySide6/Qt6)
  └─ Services          lógica de negócio, notificam o event_bus
       └─ Repositories  acesso a dados
            └─ Models    entidades do domínio
                 └─ Database (SQLite + migrations)
```

Comunicação lateral entre views via **EventBus** (`core/event_bus.py`) —
ver [ADR-009](adr/ADR-009-EventBus.md).

## Fluxo de inicialização

`main.py` instrumenta cada etapa em `%LOCALAPPDATA%\CentralGestao\logs\boot.log`:

```
[BOOT] início do main
[BOOT] configurações carregadas
[BOOT] migrations/banco executados
[BOOT] QApplication criada
[BOOT] MainWindow instanciada
[BOOT] MainWindow showEvent isVisible=True ...
[BOOT] MainWindow.show() chamado
[BOOT] threads ativas: ['MainThread', 'TaskQueueWorker']
[BOOT] app.exec() iniciado
[BOOT] primeiro paint recebido
```

As duas últimas linhas são as que realmente provam que o app funciona:
`showEvent` confirma visibilidade e `primeiro paint recebido` confirma
renderização. Um build pode compilar com sucesso e mesmo assim nunca pintar.

## Banco de dados

SQLite em `%LOCALAPPDATA%\CentralGestao\database\novo_cerebro.db`.

| Métrica | Valor |
|---|---|
| Arquivos de migration | **25** (`database/migrations/`) |
| `schema_version` | **26** |

**Arquivos ≠ versão do schema** — ver [ADR-007](adr/ADR-007-Migrations.md).

Tabelas principais:
`projects`, `tasks`, `task_deadlines`, `alerts`, `events`, `agenda_items`,
`task_dependencies`, `knowledge_pages`, `attachments`, `entity_links`,
`activity_logs`, `ideas`, `notes`.

Acesso via Repository pattern (`database/repositories/`), sobre
`BaseRepository` — ver [ADR-010](adr/ADR-010-RepositoryPattern.md).

### Armadilha: caminhos de banco

`config.DB_PATH` resolve para `%LOCALAPPDATA%` quando **empacotado**, e para a
**raiz do repositório** quando roda do código-fonte. Testes automatizados que
gravam no banco **precisam** redirecionar `config.DB_PATH` antes de qualquer
import, senão alteram o banco do desenvolvedor.

Ver o padrão em `tests/smoke_deadline.py`, que tem trava que aborta se o
redirecionamento falhar.

## Arquitetura Qt

Padrões em uso:

- **Navegação**: `QStackedWidget` na sidebar
- **Design System**: tudo visual vem do `GLOBAL_STYLE` em `gui/theme.py`.
  Componentes reutilizáveis em `gui/components/`
  (`buttons.py`, `card.py`, `page_header.py`, `context_menu_qt.py`).
- **Rich text com links clicáveis**: `QTextBrowser`
- **Autocomplete `[[` e `{{`**: `gui/widgets/wiki_text_edit.py`
- **Calendário com dia atual destacado**: `style_calendar_today()` +
  monkey-patch de `setCalendarPopup` em `main.py`
- **Tabelas com reordenação e drop**: `gui/components/drag_drop_tree_qt.py`

### Regra do Design System

> Nunca aplique `setStyleSheet` local em componente que já existe.
> Stylesheet local tem precedência sobre o `QApplication` e anula o tema.

É por isso que `gui/components/buttons.py` só define `objectName` e não
estilo — o visual vem do `GLOBAL_STYLE`. Para um visual novo, acrescente uma
variante `#nome` no `GLOBAL_STYLE` e uma classe no componente.

## Timeline / Gantt

Implementação própria com `QPainter`, **sem** widgets por item:

- `gui/components/timeline/gantt_tree_qt.py` — `GanttTree`, uma
  `QTreeWidget` com a timeline **pintada por cima** da coluna 2
- `gui/components/timeline/timeline_header.py` — cabeçalho de dias/meses
- `gui/components/timeline/timeline_geometry.py` — matemática de datas/zoom
- `gui/components/timeline/timeline_mapper.py` — tarefas → `TimelineItem`

Motivo: uma coluna única elimina a dessincronização entre árvore e canvas que
acontecia com o desenho anterior (árvore + `QScrollArea` + canvas separados).

## Métricas do código (2026-10-13)

| Métrica | Valor |
|---|---|
| Arquivos `.py` | **128** |
| Linhas de código | **20.753** |
| Arquivos de migration | 25 |
| ADRs | 11 |

> Números antigos em documentos anteriores diziam "110 arquivos / 22.898
> linhas". A contagem **caiu** porque a etapa de limpeza removeu ~484 KB de
> código morto. Meça de novo em vez de confiar neste número.