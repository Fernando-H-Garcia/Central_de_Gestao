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
