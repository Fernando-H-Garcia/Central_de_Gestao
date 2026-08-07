## Goal
- Maintain a documentation/wiki system with formatting tools, reference integrity, safe entity deletion/archiving, clickable links in activity logs, centralized calendar today-highlight, and a new Activity Summary view
- **Redesign Visual**: Modernizar toda a interface com Design System unificado (cores, tipografia, espaçamentos, componentes reutilizáveis), sem alterar regras de negócio

## Constraints & Preferences
- Formatting toolbar must have white tooltip text on dark background
- New wiki pages open in edit mode automatically
- Title must be editable in edit mode (QLineEdit)
- When switching pages/windows with unsaved changes, prompt only with "Salvar" and "Descartar" buttons centered
- "Descartar" must actually revert content (including DB undo)
- No autosave — save only on explicit "Salvar" click
- When deleting an entity that is referenced elsewhere, show impact analysis with yellow triangle, reference list grouped by type, and three buttons: Arquivar, Excluir tudo (red), Cancelar
- Arquivar keeps references intact; Excluir tudo removes all references then deletes
- Excluded references are replaced with "Nome (tipo excluído)" in wiki pages and activity logs
- All attachments from ALL pages appear in the `{{ }}` autocomplete, not just current page's attachments
- Archived docs must be viewable via a toggle button in the sidebar, with context menu limited to Desarquivar + Excluir
- Attachments are not archived; they stay in the list
- `[[` and `{{` autocomplete must work in any text entry (wiki editor, task activity dialog)
- Activity log links (`[[ ]]`, `{{ }}`) must be clickable; edit disabled for auto-generated logs, only MANUAL/COMENTÁRIO are editable
- Every `QDateEdit`/`QDateTimeEdit` calendar popup must highlight today's date in blue
- Calendar styling must work in dark theme

## Progress
### Done
- `complete_alert_silent` and `snooze_alert_silent` methods added to `AlertService` (write DB, no event emit)
- `_handle_snooze` custom path defers DB write with `QTimer.singleShot(0, …)` to avoid crash during popup close
- `_handle_complete` defers `self.accept()` with `QTimer.singleShot(0, …)` to prevent segfault
- Periodic alarm timer interval reduced from 30s to 10s in `project_360_qt.py`
- Anti-stuck detection added for `_alarm_popup_open` (resets if True > 60s)
- Exception logging to `app_errors.log` added in `_check_and_show_alarms`
- Formatting toolbar created in `wiki_qt.py`: buttons with icon+text (`# Título 1`, `B Negrito`, `• Lista`, `🔗 Link`, etc.), panel width 95px, button height 26px, visible only in edit mode
- `QToolTip` global stylesheet applied for white text on dark `#1e1e3a` background
- New wiki pages open in edit mode (`_new_page` → `edit_mode=True`)
- Title changed to `QLineEdit` (`title_edit`), toggle read-only with read/edit mode
- `hideEvent` added to prompt unsaved changes when switching tabs/windows
- `_confirm_save_before_leave` dialog: removed Cancel button, only "Salvar" and "Descartar" (centered via `QDialogButtonBox.setCenterButtons`)
- "Descartar" reverts content in UI and DB (restores `_original_page`), undoing any autosave
- Autosave removed entirely (`_autosave_timer`, `_autosave` method deleted; `_on_text_changed` is no-op)
- `save_page()` calls `_set_read_mode()` after non-silent save
- `_original_page` updated only on explicit save (`silent=False`)
- `load_pages()` auto-selects first page if `current_page is None`
- File URL bug fixed: `file://uuid` → `file:///uuid` (three slashes) so Qt parses UUID as path
- `_get_attachable_files` queries ALL attachments (`SELECT * FROM attachments WHERE deleted_at IS NULL`) across all pages
- `ReferenceWarningDialog` created at `gui/dialogs_qt/reference_warning_dialog_qt.py`
- `find_references_to_entity` and `delete_all_references_to` methods added to `LinkService` (entity_links + `{{ }}` content scan)
- `delete_all_references_to` now scans ALL wiki pages and activity logs, replacing `[[type:id|Title]]` → `Title (tipo excluído)` and `{{uuid|name}}` → `name (arquivo excluído)`
- `_delete_page` in `wiki_qt.py` checks references before delete; uses dialog actions (archive/delete_all/cancel); always calls `delete_all_references_to` before actual deletion
- Archived toggle (`btn_archived`) added in wiki sidebar, calling `toggle_archived`/`load_pages` with `show_archived` flag
- Archived wiki items context menu shows only Desarquivar + Excluir; `_restore_page` method added
- Project, task, and attachment delete handlers all check references; always call `delete_all_references_to` before deletion
- `ReferenceWarningDialog` now accepts `show_archive` parameter — hides Arquivar button for attachments
- `WikiTextEdit` reusable widget created at `gui/widgets/wiki_text_edit.py` — `[[` / `{{` autocomplete extracted from wiki_qt.py
- `render_links_as_html()` helper converts `[[ ]]` → `<a href="app://type/id">` and `{{ }}` → `<a href="file:///uuid">` for rich text display
- `task_detail_qt.py`: activity dialog uses `WikiTextEdit`; "Detalhes" column uses `QTextBrowser` cell widgets with clickable links via `_on_activity_link_clicked`
- `_on_activity_link_clicked` navigates entity on `app://` links and opens file on `file:///` links
- Context menu for activity logs restored: uses `indexAt` instead of `itemAt`, emoji icons added, `QTextBrowser.setContextMenuPolicy(NoContextMenu)` to avoid native menu
- `_open_page` re-fetches page from DB to reflect reference cleanup changes
- `QCalendarWidget` dark theme stylesheet added to `GLOBAL_STYLE` in `gui/theme.py`
- `style_calendar_today(date_edit)` helper function created — highlights today in blue via `setDateTextFormat`, re-applies on `currentPageChanged`
- Monkey-patch in `main.py` intercepts `QDateEdit.setCalendarPopup` and `QDateTimeEdit.setCalendarPopup` for ALL instances; uses `ChildPolished` event filter + `QTimer.singleShot(0, …)` to reliably apply today highlight
- `"+ Novo Alarme"` button added in task detail agenda's Alarmes sub-tab, opens `AlarmDialogQt`
- Cleared `app_errors.log` on demand; fixed `QListWidgetItem` missing import in `wiki_text_edit.py`
- **Activity Summary view** (`gui/views/activity_summary_qt.py`): new sidebar nav button "Resumo Atividades" below Projetos
  - Command panel: labels above fields (Projeto | Número de Registros | Buscar), QGridLayout
  - Results grouped by project (orange header) then task (orange title)
  - Each activity log entry shows: green date (`[dd/mm/aaaa HH:MM]`), colored action type, rendered detail text
  - Action types: CRIADO (green), ATUALIZADO (blue), MUDANÇA DE STATUS (orange), COMENTÁRIO (pink)
  - Link rendering: `[[ ]]` and `{{ }}` are clickable via `QTextBrowser` + `_on_link_clicked`
  - Detail text is human-friendly (e.g., "prazo de '25/06' para '26/06'")
  - Results limited per task (not per project) by the record count — all tasks always shown
  - QTextBrowser uses QSizePolicy.Expanding (no fixed textWidth), left-aligned content
  - New nav button added in `main_window_qt.py` at index 2; all existing indices shifted accordingly
- **Navigation back-button redesign** in `main_window_qt.py` (fixes: project→task→subtask→back must go to task, doc→link→entity→back must return to doc, task→log link→back must return to that task)
  - `_nav_history` now stores target tuples (`("page", idx)` / `("project", id)` / `("task", id)`) instead of widget references — deleted widgets no longer corrupt history
  - `_current_target` tracks current location; `_project_views` / `_task_views` caches keep live views (state preserved, no recreation)
  - `show_project_360` / `show_task_detail` always push current target before switching (even task→subtask)
  - `_navigate_back` pops until a target different from current is found, then shows it via internal `_show_project`/`_show_task`/`_show_page` without re-pushing (avoids ping-pong)
  - Removed dead `_restore_nav_button`; `_deselect_nav_buttons` helper added
  - `isVisible()` guards added to `_check_alarms_periodically` (project_360_qt.py) and `load_agenda` (task_detail_qt.py) so cached hidden views don't fire alarm popups or background reloads
- **Hierarquia de tarefas** (subtarefas visíveis na árvore do Project360Qt)
  - `get_tasks_by_project` agora inclui subtarefas (removido filtro `parent_task_id is None`) em `core/data_context.py` e fallback em `services/task_service.py`
  - Nova coluna "Progresso" (6ª) com `ProgressBarDelegate` (mini barra `x/y` concluídas/diretas)
  - Árvore colapsada por padrão (`collapseAll()` em vez de `expandAll()`)
  - **Preservação de expansão**: `load_data` captura os ids das tarefas expandidas antes do `clear()` (`expanded_ids`) e re-expande após recriar a árvore — um drop/refresh não colapsa mais a visualização expandida
  - Órfãs promovidas ao nível raiz quando o pai é filtrado por status (`visible_ids`/`orphan_ids`)
  - Indicadores/progresso do projeto agora contam todas as tarefas, incluindo subtarefas
  - Workaround ADR-005 atualizado: delegates de coluna removidos também para col 5
- **Menu de contexto em subtarefas** (`task_detail_qt.py` `tbl_subtasks`)
  - `show_subtasks_context_menu` com Abrir, Editar, Mudar Status, Criar Alarme, Arquivar/Desarquivar, Excluir
  - Handlers: `_subtask_at`, `_change_subtask_status`, `_edit_subtask`, `_delete_subtask`
  - `action_archive`/`action_unarchive` inicializados como `None` (evita NameError no elif)
- **Arquivar/restaurar recursivo** em `services/task_service.py`
  - `archive_task`/`restore_task` arquivam/restauram toda a subárvore (filhas acompanham)
  - `_get_subtree_ids` usa repo direto com `include_archived=True` (snapshot só tem ativas)
  - `soft_delete_task` também recursivo via `_get_subtree_ids`
- **Migração de tarefa/subtarefa (reparent)**
  - `move_task(task_id, new_parent_id)` no `TaskService` — previne ciclo (rejeita self e mover para própria subárvore); `new_parent_id=None` = raiz
  - `DragDropTreeWidget.dropEvent` lê `source_item.parent()` após `super().dropEvent` e emite `item_moved(task.id, new_parent)` via `QTimer.singleShot(0, …)`
  - Sinal alterado para `item_moved = Signal(int, object)` (task_id, new_parent_id) — atualizado em `project_360_qt.py` e `tasks_qt.py`
  - `handle_row_moved` persiste reparent via `move_task` e reverte com `load_data()` se falhar; interpolação de posições preservada
  - `TaskDialogQt`: combo "Tarefa Pai" (`_populate_parent_tasks`) filtra por projeto selecionado e exclui self+descendentes (`get_descendant_ids`); `_on_project_changed` repopula ao trocar projeto; migração também por edição
  - `get_descendant_ids` exposto no `TaskService` para o diálogo
- **Fix drop: subtarefa → tarefa ao soltar entre/vazio** (`gui/components/drag_drop_tree_qt.py`)
  - `dropEvent` agora calcula `new_parent` ANTES do `super().dropEvent()` com base em `dropIndicatorPosition()`: `OnItem` → filho do item alvo; `AboveItem`/`BelowItem` → irmão no nível do alvo; `OnViewport`/espaço vazio → raiz (`None`)
  - Evita o comportamento anterior de ler `source_item.parent()` após o drop (Qt colocava a subtarefa dentro de tarefa existente)
  - **V2**: drops em espaço vazio dentro da subárvore usam `_nearest_row_item(pos)` (ancora no item mais próximo acima) — se o âncora tem pai, o novo pai é esse pai (mantém a tarefa dentro da área do pai em vez de promovê-la à raiz); só vira raiz quando o âncora é um item de nível raiz
  - **V3 (`set_drop_root_parent`)**: novas árvores locais (ex.: `tbl_subtasks` no TaskDetailQt) definem `_drop_root_parent_id` = tarefa atual. Em árvores locais, drops ON/ENTRE itens de topo e em espaço vazio abaixo REDEFINEM o pai para a tarefa âncora (filho da âncora no topo NUNCA vira tarefa raiz do projeto). Em Project360/Tasks esse valor é `None` → comportamento com nível raiz
  - Em árvores locais o drop "entre X/Y" e "vazio abaixo" reordena/persiste dentro do pai âncora via `_persist_subtree_order` (reescreve `position` por irmãos na ordem visual) + `load_subtasks` agora ordena filhos por `position`
- **Subtarefas no TaskDetailQt agora são uma árvore expansível** (`gui/views/task_detail_qt.py`)
  - `tbl_subtasks` trocado de `QTableWidget` para `DragDropTreeWidget` com 5 colunas (ID, Título, Status, Prazo, Progresso)
  - `load_subtasks` constrói recursivamente toda a subárvore de descendentes com `create_tree_item`/`SortableTreeWidgetItem`, usa `task_repo.get_all(include_archived=True)` e `expandAll()`
  - Coluna Progresso com `ProgressBarDelegate` (x/y subtarefas concluídas/diretas)
  - `open_subtask`/`_subtask_at` passam a ler `item.data(0, Qt.UserRole)`; `_subtask_moved` persiste reparent via `move_task` + recarrega
- **Logs de atividade amigáveis para reparenting** (`services/task_service.py`, `gui/views/task_detail_qt.py`, `gui/views/activity_summary_qt.py`)
  - `move_task` agora registra `parent_task_id` como `{"from": old, "to": new}` no JSON
  - Formatadores (TaskDetail logs + Activity Summary) exibem "virou filho de '<título do pai>'" ou "virou tarefa raiz" em vez do id cru
  - Helper `_parent_task_title` no `activity_summary_qt.py` resolve título do pai via `TaskRepository`
- **Resumo de Atividades cascateado por hierarquia** (`gui/views/activity_summary_qt.py`)
  - Query inclui `t.parent_task_id`; cada tarefa renderiza um `QFrame` contêiner aninhado (recursivo) com `border-left` laranja translúcido — filhos ficam encaixados dentro do bloco do pai, deixando a contenção visual inequívoca
  - Linhas de log ganham `border-left` de 3px na cor da ação + indentação; contêineres filhos adicionam fundo levemente laranja (`rgba(230,126,34,0.04)`)
  - Pais sem logs não aparecem (só tarefas com atividade); filhos órfãos promovidos à raiz
- **Seções recolhíveis no Resumo de Atividades** (`gui/components/collapsible_section_qt.py`, `gui/views/activity_summary_qt.py`)
  - Novo componente reutilizável `CollapsibleSection` (header clicável com seta ▼/▶, recolhe/expande o corpo)
  - Projetos e cada tarefa (incluindo filhas aninhadas) renderizados como `CollapsibleSection` — permite recolher um projeto/tarefa para focar nos demais
  - Header azul/VR anexa propriedades `project_id`/`task_id`, menu de contexto e duplo clique de navegação preservados
  - **Indicadores de profundidade**: `CollapsibleSection` aceita `depth` — cabeçalho ganha borda-guia vertical esquerda com largura proporcional ao nível (2px*de) e ton de fundo decrescente; corpo é indentado `8 + depth*18`px; título dos níveis ≥1 ganha ramo `└─`
- **Indicadores de hierarquia na árvore de tarefas** (`project_360_qt.py`, `tasks_qt.py`, `task_detail_qt.py`)
  - `create_tree_item` agora recebe `depth`; subtarefas ganham prefixo de ramo `└─ ` (indentação proporcional à profundidade), título colorido por nível (laranja `#e67e22` nível 1, roxo `#b06ab3` nível ≥2) e leve fundo por profundidade
  - Itens de nível raiz permanecem inalterados (branco/sem fundo) — hierarquia clara por código de cor + marcador de ramo + sangria nativa
- **Recarga de subtarefas no TaskDetail** (`gui/views/task_detail_qt.py`)
  - `showEvent` recarrega `load_subtasks()` toda vez que a view fica visível (não só na primeira exibição) — views cacheadas no `main_window` (`_task_views`) refletem reparenting feito em outra tela (ex.: drag & drop)
- **Expansão em cascata no Project360** (`gui/views/project_360_qt.py`)
  - `tbl_tasks.itemExpanded` conectado a `_on_item_expanded`: um clique na seta expande recursivamente toda a subárvore (basta expandir a "1" para ver "2","3","4","5"...)
  - Cada nível mantém a própria seta para expandir/recolher individualmente
- **Fix: setas de expansão recortadas em árvores profundas** (`gui/components/drag_drop_tree_qt.py`)
  - **Causa**: Qt desenha a seta no início da 1ª coluna, deslocada pela indentação acumulada (`indent * depth`). A coluna 0 (ID) tinha largura fixa (~100px) e indentação `20px/nível`; a partir de ~5 níveis a seta saía da coluna e era recortada (sumia)
  - **Fix**: nova função `fit_branch_arrows(tree)` reduz a indentação gradualmente (20→16→14→12px conforme a profundidade) e alarga a coluna 0 (`indent*max_depth + 30`) para a seta sempre caber; aplicada no fim do `load_data` do 360/tasks_qt e do `load_subtasks` do task_detail
  - Não há limite de profundidade no código — as setas continuam aparecendo em qualquer nível

### In Progress
- (none)

### Blocked
- (none)

## Redesign Visual – Plano de Implementação

### Sprint 1 – Design System
- **Cores**: criar constantes centralizadas (`BACKGROUND_PRIMARY`, `TEXT_PRIMARY`, `PRIMARY_BLUE`, `BORDER_SUBTLE`, etc.)
- **Tipografia**: padronizar tamanhos, pesos, line-height e espaçamentos (`XS=4`, `SM=8`, `MD=16`, `LG=24`, `XL=32`)
- **Bordas**: padronizar raios (pequeno, médio, grande)
- **Sombras**: apenas dois níveis (card, popup)

### Sprint 2 – Componentes Reutilizáveis
- **Botão Primário**: Nova tarefa, Novo projeto, Salvar etc.
- **Botão Secundário**: Editar, Cancelar, Voltar
- **Botão Texto**: Links, Referências, Abrir
- **Cards**: componente único de card para todos os painéis
- **Badges**: para status, prioridade, saúde, categoria (nunca texto colorido solto)
- **Barra de Progresso**: componente reutilizável para projeto/tarefa

### Sprint 3 – Barra Lateral
- Redesenho completo: mais limpa, menos pesada, mais moderna
- Adicionar ícones
- Itens: Monitor, Projetos, Agenda, Documentação, Wiki, Resumo, Configurações
- Hover suave, item ativo destacado, transições

### Sprint 4 – Cabeçalho das Páginas
- Padronizar todos os cabeçalhos (nome, objetivo, status, prioridade, prazo, progresso)
- Evitar excesso de linhas horizontais, mais espaço em branco

### Sprint 5 – Cards de Indicadores
- Redesenhar: mais leves, sem bordas pesadas, maior destaque para números
- Cada card: ícone, número, descrição

### Sprint 6 – Tabelas
- Remover excesso de linhas, aumentar altura das linhas, melhor espaçamento
- Hover, seleção elegante, linhas alternadas
- Status e prioridade como badges (não texto colorido)
- Datas críticas com cores de alerta

### Sprint 7 – Ícones
- Adicionar ícones em projetos, agenda, wiki, referências, editar, novo, voltar
- Auxiliar leitura sem excesso

### Sprint 8 – Espaçamento
- Revisar toda a interface: margens consistentes entre cards, tabelas, cabeçalhos, botões, menus

### Sprint 9 – Hierarquia Visual
- Usar tamanho, peso e contraste (não apenas cor) para indicar: onde está, projeto aberto, progresso, atenção, ações principais

### Sprint 10 – Padronização Global
- Todas as telas compartilham: botões, cards, badges, tabela, cabeçalho, barra de progresso, menus
- **Revisar hover/pressed de todos os botões**: Voltar, +Novo Evento, Buscar, Arquivados, +Novo Projeto, etc. Garantir que hover mude cor e pressed mantenha feedback visual consistente
- **Revisar tabelas de alarmes/agenda** (alarm_tree_qt.py, agenda_tree_qt.py): estilo dos cabeçalhos de grupo, cores das prioridades, espaçamento entre linhas

### Restrições
- Não alterar funcionalidades, estrutura do banco, lógica das telas, atalhos nem remover funcionalidades
- Foco exclusivamente visual

### Ordem de Implementação
1. Design System (cores, tipografia, espaçamentos)
2. Componentes reutilizáveis (botões, cards, badges, barra de progresso)
3. Barra lateral e cabeçalhos
4. Tabelas e listas
5. Aplicar gradualmente em todas as telas

## Key Decisions
- Autosave removed entirely because it conflicted with "Descartar" — the 1.5s timer would save content before the user could switch pages, making discard impossible
- `_original_page` snapshot updated only on explicit save so that `_has_unsaved_changes` remains accurate after autosaves
- Reference checking implemented via `entity_links` table for `[[ ]]` patterns and content regex scan for `{{ }}` patterns; no new schema needed
- Three-slash URL `file:///uuid` used because Qt's `QUrl` parses `file://uuid` as host=uuid/path=empty, making `url.path()` empty
- Archived pages are loaded from `get_all_archived()` instead of a flag on the tree, keeping the display logic simple
- `delete_all_references_to` always runs before entity deletion (not only on "Excluir tudo" action) to guarantee broken links are never left dangling
- `QChildEvent` event filter + `QTimer.singleShot(0, …)` used to apply calendar today-highlight because `calendarWidget()` returns `None` until the popup is first shown
- Monkey-patching `setCalendarPopup` chosen over subclassing to avoid modifying every dialog file
- Activity Summary is a top-level nav item (sidebar button), not a sub-view, for simplicity

## Critical Context
- Error message `QWindowsWindow::setGeometry: Unable to set geometry…` is a harmless Qt/Windows warning when minimum window size exceeds screen space
- `` ` `` in Markdown / autocomplete uses two‑character triggers (`[[`, `{{`) and the filtering is done via `.lower()` substring match on entity titles
- The `entity_links` table stores `source_type`/`source_id`/`target_type`/`target_id`/`relationship_type` — sources are always wiki pages when created by `update_links_from_text`
- `find_references_to_entity` also scans wiki page content for `{{uuid}}` patterns to find file references not tracked in `entity_links`
- `KnowledgePageService` uses `self.page_repo` (not `self.repository`); `AttachmentService` uses `self.repository`
- Segfault in `_handle_complete` / `_handle_snooze` was caused by calling `self.accept()` inside the button slot while widget destruction was pending; fixed by deferring with `QTimer.singleShot(0, …)`

## Build Procedure (EXE + Installer)

### Prerequisites
- Python **3.11** (3.12+ causes PySide6 compatibility issues)
- PySide6 **6.6.x** (any 6.11+ breaks on Python 3.11 → `DLL load failed while importing QtWidgets`)
- PyInstaller **6.21+**
- Inno Setup 6 (`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`)
- `VC_redist.x64.exe` at project root (optional but recommended)

### Step-by-step

1. **Create venv** (one-time):
   ```powershell
   & "C:\Anaconda\python.exe" -m venv venv_build
   ```

2. **Install deps with correct versions** (critical — must be PySide6 6.6.x):
   ```powershell
   .\venv_build\Scripts\pip.exe install "PySide6>=6.6,<6.7" "pyinstaller>=6.21,<7.0" Markdown>=3.5
   ```

3. **Verify compatibility** (must succeed without ImportError):
   ```powershell
   .\venv_build\Scripts\python.exe -c "import PySide6; from PySide6 import QtCore; print(f'PySide6: {PySide6.__version__}, Qt: {QtCore.qVersion()}')"
   ```

4. **Criar seed DB limpo** (substitui `database/novo_cerebro.db` por schema-only):
   ```powershell
   .\venv_build\Scripts\python.exe -c "
   import sqlite3, os
   from pathlib import Path
   db = Path('database/seed_empty.db')
   if db.exists(): db.unlink()
   conn = sqlite3.connect(str(db))
   conn.executescript('PRAGMA foreign_keys = ON;'); conn.commit()
   for f in sorted(Path('database/migrations').glob('*.sql')):
       if f.stem.split('_')[0].isdigit():
           v = int(f.stem.split('_')[0])
           sql = f.read_text(encoding='utf-8')
           try:
               conn.executescript(sql); conn.commit()
               conn.execute('INSERT OR REPLACE INTO schema_version (version) VALUES (?)', (v,)); conn.commit()
           except sqlite3.OperationalError as e:
               if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower(): pass
               else: raise
   conn.close()
   bak = Path('database/novo_cerebro.db.bak')
   orig = Path('database/novo_cerebro.db')
   if orig.exists(): orig.rename(bak)
   db.rename(orig)
   print(f'Seed limpo: {orig} ({os.path.getsize(orig)} bytes) | Backup: {bak}')
   "
   ```

5. **Build EXE + Installer**:
   ```powershell
   .\venv_build\Scripts\python.exe scripts\build\build_release.py --release
   ```

6. **Restaurar banco original** (remove seed, volta o backup):
   ```powershell
   Move-Item database\novo_cerebro.db.bak database\novo_cerebro.db -Force
   Remove-Item database\seed_empty.db -ErrorAction SilentlyContinue
   ```

7. **Expected artifacts**:
   - `build\dist\CentralDeGestao.exe` — **~46 MB** (one-file mode, self-contained)
   - `build\CentralDeGestao_Installer.exe` — **~70 MB** (includes VC++ Redist)

8. **Copy installer**:
   ```powershell
   Copy-Item build\CentralDeGestao_Installer.exe ..\Executaveis\ -Force
   ```

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `DLL load failed while importing QtWidgets` | PySide6 6.11+ on Python 3.11 | Install PySide6 6.6.x (`pip install "PySide6>=6.6,<6.7"`) |
| EXE is 2.5 MB (too small) | `.spec` is in one-folder mode (COLLECT) | Remove COLLECT, EXE must include `a.binaries, a.zipfiles, a.datas` |
| `PERFORMANCE_DEBUG = True` causes excessive I/O | Set to `False` in `utils/instrumentation.py:4` |
| App crashes writing logs to `Program Files` | `LOGS_DIR` resolves to wrong path | Check `config.py:LOGS_DIR` — must use `data_root()` → `%LOCALAPPDATA%\CentralGestao\logs\` when bundled |
| App doesn't start, no visible window | Boot instrumentation helps debug | Check `%LOCALAPPDATA%\CentralGestao\logs\boot.log` for last successful step |

### Build architecture
- **Spec**: `CentralDeGestao.spec` at project root — `console=False`, `icon='app.ico'`, one-file mode
- **Boot log**: Written to `%LOCALAPPDATA%\CentralGestao\logs\boot.log` with timestamps per step
- **Data dir**: `%LOCALAPPDATA%\CentralGestao\` (DB, config, logs, backups, attachments)
- **No __file__ in log paths**: All paths use `utils.paths.data_root()` which returns `%LOCALAPPDATA%/CentralGestao` when bundled
- **Single process**: Only `subprocess.Popen(["explorer", ...])` allowed (open files in Windows Explorer)
- **Boot instrumentation in main.py**: Reports `início do main`, `configurações carregadas`, `migrations/banco executados`, `QApplication criada`, `MainWindow instanciada`, `MainWindow.show() chamado`, `app.exec() iniciado`
- **showEvent/paintEvent in main_window_qt.py**: Confirms window is actually visible and painted

## Relevant Files
- `gui/views/wiki_qt.py`: Formatting toolbar, title_edit auto-selection, archived toggle, delete‑with‑reference‑check, all‑attachments lookup, `_confirm_save_before_leave` (Salvar/Descartar only, no autosave), `_set_read_mode`/`_set_edit_mode` toolbar toggle, `_restore_page`
- `gui/dialogs_qt/reference_warning_dialog_qt.py`: Dialog with yellow triangle, reference list, three action buttons (Arquivar, Excluir tudo, Cancelar), `show_archive` parameter
- `services/link_service.py`: `find_references_to_entity()`, `delete_all_references_to()` (scans wiki pages + activity logs, replaces with `"(tipo excluído)"`), `_type_label()`
- `gui/widgets/wiki_text_edit.py`: `WikiTextEdit` (reusable `[[`/`{{` autocomplete), `render_links_as_html()` converter
- `gui/views/task_detail_qt.py`: `WikiTextEdit` in activity dialog; `QTextBrowser` cell widgets with clickable links; `_on_activity_link_clicked`; `new_alarm` button; `indexAt`-based context menu; `NoContextMenu` on QTextBrowser
- `gui/views/projects_qt.py`: Project delete handler with reference check
- `gui/views/tasks_qt.py`: Task delete handler with reference check
- `gui/views/project_360_qt.py`: Task delete handler with reference check; alarm timer 10s; anti-stuck; `_check_and_show_alarms` exception logging
- `gui/theme.py`: `QCalendarWidget` dark stylesheet, `style_calendar_today()` helper
- `main.py`: Monkey-patch for `QDateEdit`/`QDateTimeEdit.setCalendarPopup` with `ChildPolished` event filter
- `services/alert_service.py`: `complete_alert_silent`, `snooze_alert_silent` methods (no event emission)
- `gui/dialogs_qt/alarm_popup_qt.py`: `_handle_complete` / `_handle_snooze` fixed to defer `self.accept()` via timer; exception logging; `_remove_card` no longer calls `accept()`
- `gui/dialogs_qt/alarm_dialog_qt.py`, `project_dialog_qt.py`, `task_dialog_qt.py`, `schedule_dialog_qt.py`, `event_dialog_qt.py`, `alarm_popup_qt.py`: all patched with `style_calendar_today` (now redundant due to monkey-patch)
- `gui/main_window_qt.py`: Sidebar nav buttons (Monitor, Projetos, Resumo Atividades, Agenda Geral, Documentação), `_on_global_navigate` for wiki nav at index 4
- `gui/views/activity_summary_qt.py`: Activity summary view with project filter, record count, grouped results, clickable links, human-readable detail formatting
- `logs/app_errors.log`: Exceptions from popup handlers, slot crashes logged here
