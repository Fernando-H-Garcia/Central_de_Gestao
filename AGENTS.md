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
- **Botões toggle (ativar/desativar, `QPushButton` checkable)**: devem seguir o padrão de estado — LIGADO = fundo preenchido colorido + texto branco (realça semântica, ex.: verde `#2b8c52` para "concluídos", hover `#3bbf6e`); DESLIGADO = transparente + borda `#555` + texto `#aaa` (hover: fundo `#2d2d55` + borda `#4a6fe3`); sufixo do texto indicando o estado (`OFF`/`ON`)

## Progress
### Done
- **Prazo Estimado (marcador vermelho)** (migration 022, models/entities.py, task_repository.py, timeline_mapper.py, gantt_tree_qt.py, timeline_view_qt.py, project_360_qt.py): novo campo tasks.estimated_deadline DATE; botao direito na tarefa -> Prazo Estimado abre dialogo de data (com Remover); bandeira vermelha na linha da tarefa; arrastavel (dias inteiros) com deadline_moved(task_id, data); menu no marcador: Editar Prazo / Abrir Tarefa / Excluir Prazo; duplo clique edita; tooltip Prazo Estimado; persistencia via repo direto + load_data; **halo de hover no marcador** (mesmo estilo dos eventos, `_hover_deadline_id`); **pre-preenchimento**: prazo existente > data sob o mouse (timeline, `edit_deadline_at_requested`) > hoje (janela Tarefas); **2 alarmes automaticos** (migration 23: `deadline_alarm_week`/`deadline_alarm_day` guardam os ids) — 1 semana antes + dia do prazo; mover o prazo atualiza as datas dos alarmes (edicoes manuais de titulo/hora preservadas); excluir o prazo remove os 2 alarmes (`_sync_deadline_alarms`)
- **Checkbox clara padronizada** (gui/theme.py CHECKBOX_STYLE): texto branco + indicador visivel (fundo #2a2a3f, borda #9a9ab8, marcado #4a6fe3); aplicada nas checkboxesHora especifica (alarme) e E um Marco (tarefa) - usar esse estilo em QUALQUER QCheckBox nova em dialogo
- **Planejamento (Gantt) UNIFICADO em um único widget** (`gui/components/timeline/gantt_tree_qt.py` novo, `timeline_view_qt.py` reescrito, `timeline_header.py` ajustado)
  - Motivação: sincronização árvore↔canvas nunca ficava perfeita; usuário pediu UMA coluna única
  - `GanttTree(QTreeWidget)` = árvore + timeline embutida: col 0 título, col 1 resumo, col 2 linha do tempo (barras/grid/eventos/hoje pintados no `paintEvent` por cima da árvore, a partir de `timeline_left() = columnWidth(0)+columnWidth(1)`)
  - SEM splitter/QScrollArea/canvas/segunda scrollbar vertical — rolagem vertical é a nativa da árvore; impossível dessincronizar
  - Interações na área da timeline: clique seleciona a linha, duplo clique abre tarefa, arrastar barra muda datas (`task_moved`, preview com `_delta` durante drag), arrastar vazio faz pan horizontal (`pan_triggered`), tooltips de evento/barra
  - `TimelineHeader.set_left_margin(m)` desenha dias/meses/HOJE somente sobre a coluna da timeline (`_sync_header_margin` após `fit_branch_arrows`); HOJE na faixa inferior do header (abaixo dos dias, acima da 1ª tarefa); TODOS os dias exibidos sem pular — número vertical quando ppd < 14px
  - **`go_to_today` com lead-in de passado**: hoje fica a 40% da largura visível (não mais no centro), entrando até 1 mês de datas antes de hoje à esquerda (`lead_px = min(30×ppd, 40% da área)`)
  - **Ctrl + roda = zoom contínuo** (`gantt_tree_qt.py` `wheelEvent` → signal `ctrl_zoom_requested` → `_on_ctrl_zoom` na view): fator 1.15/step, piso 1.0 teto 200 px/dia, data do centro visível ancorada; filtros Dia/Semana/Mês restauram as escalas fixas (50/15/5); range horizontal = `anchor_date` (hoje−730d) até hoje+1095d (`update_h_scrollbar` usa 1825×ppd) — passado navegável em qualquer zoom; **Shift + roda = rolar timeline horizontalmente** (±3 dias/step via `pan_triggered`)
  - **Escadinha de números no header** (`timeline_header.py`): intervalo dos dias conforme ppd — ≥13: diário; ≥6,5: 2 em 2; ≥4,33: 3 em 3; ≥1,86: segundas-feiras; abaixo: só o 1º dia do mês (nada sobrepõe durante o zoom contínuo); rótulos de mês/ano em DOIS níveis (cima/baixo) com detecção de colisão — se não couber em nenhum nível, o rótulo é suprimido (nada sobrepõe no zoom mínimo)
  - Filtros (Concluídas/Milestones/Tarefas/Eventos/Alarmes) usam `setHidden` nativo — barras somem junto
  - **Hover na timeline**: `_hover_item_id`/`_hover_ev` rastreados no `mouseMoveEvent` (limpos no `leaveEvent`); barra em hover ganha glow translúcido + contorno branco; evento/alarme em hover ganha halo circular; hover usa `_hit_range` (inclui pais/marcos, que não arrastam — só folhas usam `_hit_bar`); **tooltip persistente** (`_tip_timer` 1s reexibe via `QToolTip.showText` enquanto hover ativo — some só ao tirar o mouse/arrastar; `_hide_tooltip` limpa estado)
  - **Menu de contexto + duplo clique** (`gantt_tree_qt.py`, `timeline_view_qt.py`, `project_360_qt.py`): botão direito em qualquer coluna → menu com "👁️ Abrir Tarefa" / "✏️ Editar Tarefa"; DUPLO CLIQUE abre a EDIÇÃO (TaskDialogQt) — `setExpandsOnDoubleClick(False)` para não conflitar com expandir/recolher (expansão só pela seta); signals `open_task_requested`/`edit_task_requested` carregam `raw_task` (fallback int id); view encaminha via `edit_task_signal`; host resolve int→repo
  - **Arraste + edição de alarmes/eventos na timeline** (`gantt_tree_qt.py`, `timeline_view_qt.py`, `project_360_qt.py`): press sobre ▲/● inicia drag (`_drag_event`, preview mutando `ev.datetime`/`end_datetime` com delta fracionário — preserva hora); release emite `event_moved(ev, novo_início, novo_fim)`; **eventos com duração têm resize pelas pontas** (`_event_with_zone` — círculos início/fim com ±7px redimensionam só um lado, ponta oposta fixa; meio move inteiro; fim nunca recua antes do início); clique simples NAO faz nada (intencional); antigo: `event_clicked` com atraso de 280ms (`_pending_ev_click`) para não conflitar com duplo clique; **duplo clique abre o EDITOR do alarme/evento** (`_on_timeline_event_clicked` → `_on_timeline_edit_event`) — não a tarefa vinculada; menu de contexto no ícone: **Abrir {Alarme|Evento}** / Abrir Tarefa / **Excluir** (`delete_event_requested` → `_delete_timeline_event` com confirmação); persistência em `_on_timeline_event_moved` (alarme: `alert_date`/`alert_time` + overdue→pending; evento: `start_datetime`/`end_datetime` ISO)
  - **Menu de contexto da tarefa no Planejamento** também oferece `🔔 Criar Alarme` / `📅 Criar Evento` (`create_alarm_requested`/`create_event_requested` → `create_alarm_signal`/`create_event_signal` → `_create_alarm_from_timeline`/`_create_event_from_timeline` no project_360)
  - **Datas de eventos na lista** (`agenda_tree_qt.py` `_format_event_date`): parse tolerante (ISO, com/sem T, microssegundos, só data) + fallback reformatando aaaa-mm-dd → dd/mm/aaaa (nada mais aparece como aaaa/mm/dd)
  - **Indicador flutuante de arraste** (`gantt_tree_qt.py` `_draw_drag_info`): janeleinha azul junto ao cursor mostrando a posição atual — tarefa: `📅 dd/mm/aaaa → dd/mm/aaaa`; alarme dia todo (sem `alert_time`): `🔔 dd/mm/aaaa (dia todo)` e **snap em dias inteiros** (hora nunca muda); alarme com hora / evento: data+hora livre preservando horário, com `→ fim` quando tem duração; some no release
  - **Resize pelas extremidades da barra** (`gantt_tree_qt.py`): arrastar os ~7px das pontas muda SÓ a data inicial (`resize_start`, nunca passa do fim) ou SÓ a final (`resize_end`, nunca recua antes do início); meio da barra move inteiro; cursor `SizeHorCursor` nas pontas; indicador mostra `⏮ Início: … · Fim: …`; persistência pelo mesmo `task_moved` (host grava start_date/due_date); **pais também redimensionam pelas pontas** (`_hit_parent_edge` — muta `manual_start/end`, meio do pai NÃO move; se o novo fim do pai < fim agregado das filhas, a faixa de aviso ⚠ aparece ao vivo)
  - **Barra do pai = datas PRÓPRIAS + aviso de estouro** (`gantt_tree_qt.py` `draw_bar`/`_draw_parent_bar`/`_draw_overrun_warning`): barra do pai usa as datas dele (independente das filhas); se o fim agregado das filhas (`item.end`) > fim do pai, desenha extensão vermelha translúcida com borda tracejada + `⚠` indicando que as filhas estouram o prazo do pai (usuário deve ajustar); hover/tooltip do pai usam as datas próprias; **MILESTONE nunca tem aviso de estouro** (`_overrun_rect` exclui `is_milestone` — marco não é prazo de pai)
  - **Milestone sem retângulo** (`draw_bar`/`_draw_milestone`): losango na data INICIAL **repetido todo mês por toda a área VISÍVEL** (não limitado pelas datas da tarefa; `_add_month`, clamp em fim de mês); **linha tracejada verde sempre visível** (percorre toda a área visível a partir da data do marco — não some no zoom entre dois losangos); hover/seleção aumenta o losango com contorno branco; cor VERDE fixa (identidade própria); **check `is_milestone` vem ANTES de `is_parent`** — pai com subtarefas que é marco desenha losangos, não retângulo (caso "Dev LATAM"); **hover/tooltip do milestone cobrem a linha tracejada TODA** (`_hit_range` trata `is_milestone`: da data em diante, sem limite superior — antes só um filete de 1 dia respondia) e o tooltip próprio mostra "Data do marco" em vez de período
  - **Regras de Milestone no TaskDialogQt** (`task_dialog_qt.py`): só FILHA de pai não-marco é bloqueada (`_on_parent_changed` desabilita/desmarca o checkbox) — tarefa RAIZ (sem pai) sempre pode ser Marco; checkbox posicionado ENTRE data início e data final, com texto branco (visível no tema escuro); marco não tem data final (`_on_milestone_toggled` desabilita `ent_due` e sincroniza due=start; save força due=start); subtarefa era-marco com pai normal é desmarcada ao abrir
  - **Linha mais compacta**: `row_height` 40→30 (`timeline_geometry.py` + `ROW_HEIGHT` no `gantt_tree_qt.py`) — menos espaço vazio acima/abaixo de cada tarefa
  - **Barra do pai com altura das filhas**: `_draw_parent_bar` usa 20px (igual às folhas), mesmo estilo
  - **Status derivado renomeado**: "EM RISCO" → "Tempo esgotando" (`timeline_mapper.py`; `bar_color` aceita ambos)
  - **Fix preview do resize**: o delta NÃO é mais somado em `draw_bar` (item.start/end já carregam o preview mutado no `mouseMoveEvent`) — antes a barra inteira deslocava ao puxar uma ponta (dupla aplicação)
  - **Tom da barra por TEMPO (não progresso)** (`draw_bar`/`_draw_parent_bar`): fundo da timeline é UNIFORME (removido o escurecimento invertido do futuro); a barra fica translúcida/apagada (alpha 90) na parte ANTES de hoje e com a cor VIVA de hoje em diante (barra que cruza hoje é pintada duas vezes com clip); tarefa "Concluído" fica sempre com a cor cheia; o antigo bicolore por progresso (`color.darker(120)`) foi removido
  - **Fundo invertido**: FUTURO (hoje→frente) escuro `#06060c`, passado com fundo normal (`_draw_past_shading`) — REVERTIDO depois: fundo uniforme em toda a timeline
  - **Recentralização no primeiro layout** (`timeline_view_qt.py` `resizeEvent` + flag `_pending_center`): populate roda antes do layout definitivo — `go_to_today` reexecutado quando a largura real chega (offset nunca fica deslocado)
  - **Linha-guia do mouse** (`gantt_tree_qt.py` `_draw_mouse_guide`/`_update_guide`/`_datetime_at_x`): linha vertical sutil segue o mouse na área da timeline com etiqueta `dd/mm/aaaa HH:MM` no topo (fração do dia calculada de x); some ao sair da timeline/widget
  - API de `TimelineViewQt` preservada (populate/set_events/signals) — project_360 não mudou
  - `timeline_canvas.py` ficou órfão (mantido no disco por referência)
- **Popup de alarmes: "Abrir Tarefa" + nome da tarefa correto** (`gui/dialogs_qt/alarm_popup_qt.py`, `main_window_qt.py`, `project_360_qt.py`)
  - **Causa do número em vez do nome**: alarmes ativos apontando para tarefas soft-deleted (ex.: tasks 53/55/56 com `deleted_at`); `task_map` vinha de `get_all_active()` (filtra deleted) → lookup falhava → fallback `"Tarefa #N"`
  - Fix: `resolve_task_title(task_id)` no popup usa `TaskService().task_repo.get_by_id()` direto (não filtra deleted) — mostra `"Título (tarefa excluída)"` para excluídas; fallback só se repo falhar
  - Novo botão `📋 Abrir Tarefa` no `AlarmCard`; popup ganhou signal `open_task_requested(int)` — fecha o modal (`accept()`) e emite via `QTimer.singleShot(0, …)` para não travar navegação durante `exec()`
  - Conexões: `main_window._check_global_alarms` → `show_task_detail`; `project_360._check_and_show_alarms` → `open_task_detail_signal.emit`
- **Timeline: alinhamento tarefa↔barra + scroll sincronizado** (`gui/components/timeline/timeline_view_qt.py`, `timeline_canvas.py`)
  - Causa raiz da dessincronia: canvas tinha `QScrollArea` própria e sync por **proporção** (`value/max`) — alturas de conteúdo divergiam (canvas tinha piso de 400px)
  - Árvore agora é FONTE ÚNICA de scroll vertical; canvas espelha offset em pixels via `set_scroll_y` (1:1, sem ratio); removidos `_on_tree_scroll`/`_on_canvas_scroll`
  - `setUniformRowHeights(True)` garante linha da árvore = `row_height` (40px) exata do canvas → barra alinha horizontalmente com a tarefa
  - Canvas: pintura em coords de conteúdo com `painter.translate(0, -_scroll_y)`; hit-test/tooltips/duplo clique ajustados (`pos.y() + _scroll_y`); altura = `n_linhas × 40px` (piso 400px removido)
  - Roda do mouse sobre o canvas repassa à árvore (`wheelEvent` → signal `wheel_scrolled`)
- **Voltar navega por abas como sub-janelas** (`project_360_qt.py`, `task_detail_qt.py`)
  - `_init_tab_navigation` registra mudanças de aba principal (`self.tabs`) e sub-abas da Agenda (`self.agenda_tabs`) numa pilha de posições `(aba_principal, sub_aba_agenda)`
  - `_on_back_clicked` (conectado ao botão Voltar) consome a pilha primeiro: volta Tarefas→Ideias→Voltar=Tarefas; Agenda→Eventos→Voltar=Alarmes; Agenda→Voltar=Ideias; só quando a pilha esgota emite `go_back` (volta pra janela anterior)
  - `_suppress_tab_nav` evita registrar mudanças programáticas feitas pelo próprio Voltar
- **Agenda Geral com sub-abas por projeto** (`gui/views/agenda_qt.py`)
  - Aba "Alarmes" e aba "Eventos" agora contêm um `QTabWidget` interno (`project_alarm_tabs` / `project_event_tabs`) com UMA sub-aba por projeto que possui itens
  - `load_data` agrupa alarmes/eventos por projeto (tarefa filha → projeto da tarefa; alarme de projeto → próprio; `project_id` nulo → "Sem Projeto"); `project_repo` resolve os nomes
  - `_rebuild_project_tabs` remove os tabs antigos (via `removeTab` + `deleteLater`), ordena por nome (Sem Projeto por último) e cria `AlarmCardsWidget`/`AgendaTreeWidget` com `grouping="date"`, `filter_project_id=<projeto>` e o lote já filtrado do grupo
  - Título do tab: `Nome do Projeto (contagem)`
  - **`_project_active`** descarta itens de projetos excluídos/arquivados no agrupamento (tabs fantasmas de resquícios de teste — ex.: "projeto 2", "outro projeto teste" — não aparecem mais; mesma regra de validação que os widgets aplicam no conteúdo, aplicada antes de criar a aba)
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
- **Listas de tarefas iniciam EXPANDIDAS** (`project_360_qt.py`)
  - O 360 era a única view que iniciava recolhida (`collapseAll()` + restauração de `expanded_ids`); trocado para `expandAll()` logo após `fit_branch_arrows`
  - Removida a coleta/restauração de expansões prévias (`expanded_ids`) — ficaria código morto com expandAll sempre
  - `tasks_qt` e `task_detail` já usavam `expandAll()`; o `itemExpanded`/`_on_item_expanded` continua funcionando para expansão em cascata manual
- **Fantasma do drag translúcido e deslocado** (`gui/components/drag_drop_tree_qt.py`)
  - Sobrescreve `startDrag` no `DragDropTreeWidget`: renderiza a linha arrastada inteira com opacidade global (`painter.setOpacity(0.55)`) — antes o Qt só aplicava transparência em badge/status e deixava título/período sólidos
  - Hotspot deslocado para a direita (`QPoint(60, h/2)`) para o fantasma não tapar a área de destino do drop
  - MIME data via `model().mimeData([index])` para manter `InternalMove` funcionando
- **Alarmes do TaskDetail filtrados por tarefa + descendentes** (`gui/views/task_detail_qt.py`)
  - Removidos os toggles "Filtrar: Todas do Projeto / Só desta Tarefa" das sub-abas Alarmes e Eventos
  - Alarmes agora mostram só os da tarefa aberta + subárvore (`subtree_ids = {task.id} ∪ get_descendant_ids`); na tela de um filho NÃO aparecem alarmes do pai; sem alarmes de projeto (`proj_alarms` removidos)
  - Eventos continuam mostrando o projeto todo (decisão do usuário — apenas alarmes foram escopados)
  - Não há limite de profundidade no código — as setas continuam aparecendo em qualquer nível
- **Alarme global — dispara em QUALQUER tela do app** (era só na Visão 360 do próprio projeto)
  - `AlertService.get_active_alarms_all(task_service)`: escaneia TODAS as tarefas ativas (não só do projeto aberto), ordena por prioridade/data
  - `main_window_qt.py`: `_setup_global_alarm_timer()` cria um `QTimer` global (10s) + `QTimer.singleShot(500)` no boot; `_check_global_alarms()` roda **sem depender de `isVisible()`**, com anti-stuck (reset se popup aberto > 60s) e log de exceção em `app_errors.log`
  - Popup usa `AlarmPopupQt` com `parent=self` (MainWindow)
  - `project_360_qt.py`: **removido** o agendamento local de alarme (timer + singleShot 400ms + `_check_alarms_periodically`) para evitar duplo-popup — o global é agora a fonte única
- **Comportamento da seta na árvore 360 sob filtro de status — INTENCIONAL, não alterar**
  - A seta (▸/▾) só aparece quando um item tem **filho visível no filtro ativo**; se todos os descendentes têm outro status, o Qt naturalmente não desenha a seta
  - Quando o pai é filtrado para fora, as subtarefas são promovidas à raiz (órfãs) — confirmado com o usuário que desse jeito está correto; não "melhorar" a hierarquia sob filtro
- **Reordenar tarefas arrastando na árvore do Planejamento** (`gui/components/timeline/gantt_tree_qt.py`, `timeline_view_qt.py`, `project_360_qt.py`)
  - `GanttTree` agora herda `TranslucentDragMixin` + InternalMove: arrastar linhas nas COLUNAS DE TEXTO reordena tarefas; a área da timeline continua com os arrastes próprios (barras/eventos/prazo) — o press só delega ao super() quando `x < timeline_left()`
  - Regras de bloco `[pai[filhas]]` — **SÓ REORDENAÇÃO LOCAL, sem mudar a composição dos blocos**: mover o PAI leva toda a subárvore junto (removeChild/insertChild preserva os filhos); ENTRE itens → irmão no nível do alvo; **SOLTAR SOBRE um item é PROIBIDO** (drop ON é convertido para BelowItem → irmão do alvo); **Só é permitido soltar dentro do PRÓPRIO GRUPO** (`_group_key` compara o id do pai por VALOR, nunca `is` — wrappers PySide6 do mesmo item C++ podem ser objetos Python distintos); filha não sai do pai dela, não entra em outra filha nem em outro pai; vazio → fim do próprio grupo
  - **Pai na RAIZ mapeia para BLOCOS**: arrastar um pai de topo e soltar em qualquer linha de outro bloco → metade de cima da 1ª linha do bloco = antes dele; mais abaixo (inclusive nas filhas) = depois do bloco inteiro (sem isso era impossível acertar a linha estreita do pai entre blocos expandidos)
  - **Movimento MANUAL no dropEvent** (NÃO chamar super().dropEvent): o drop nativo do Qt recalcula OnItem internamente e aninhava mesmo convertendo a posição — por isso o GanttTree faz removeChild/insertChild direto e aceita o evento; ajuste de off-by-one (`src_idx < row → row -= 1`) vale TAMBÉM na raiz
  - `handle_gantt_row_moved` resolve posições pelo REPO (`task_repo.get_by_id(tid).position`) — `TimelineItem` NÃO tem `.position` (AttributeError em produção)
  - **Timeline ordena por position**: o `TimelineMapper.map_tasks_to_timeline` preserva a ordem de entrada — `load_data` precisa ordenar `tasks` por `position` antes de montar `tl_main`/`tl_by_parent`, senão a reordenação grava no banco mas não muda nada na tela (bug encontrado em produção)
  - Novo signal `GanttTree.item_moved(task_id, new_parent_id)` → `TimelineViewQt.gantt_row_moved` → `project_360.handle_gantt_row_moved`: persiste reparent via `move_task` (reverte com load_data se falhar) e reescreve posições por grupo de irmãos na ordem visual do Gantt (gap 100), limpa sort indicator e emite `entity_updated`
  - `mouseReleaseEvent` agora chama `super()` no fim (fecha o ciclo press/release do Qt, necessário para o drag&drop nativo)

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

## Timeline/Gantt ("Planejamento") – Plano de Evolução

### Avaliação do usuário (baseline)
- Conceito 9/10 · Hierarquia 9/10 · Timeline 8/10 · Legibilidade 7,5/10 · Poluição visual 7/10
- **Prioridade: melhorar semântica visual, NÃO adicionar componentes** (tela já densa)
- Estado atual: implementação existente em `gui/components/timeline/` (custom painting no `TimelineCanvas`), aba "Planejamento" em `project_360_qt.py` (linhas ~224-228, ~632-666), mapeamento via `TimelineMapper` (tasks/events/alarms), agregação de datas do pai via `TimelineAggregation` (MIN filhas → MAX filhas).

### Ajustes solicitados (feedback do usuário)
1. **Tarefa pai como resumo executivo** — na árvore: `▼ Robustez engate/desengate` + linha de resumo `3 tarefas · 2 concluídas · 67% · 21/08 → 09/09`; barra do pai no canvas **sempre = MIN(início das filhas) → MAX(fim das filhas)** (a agregação já faz isso; falta a barra proeminente + texto de resumo).
2. **Cor por significado, não identidade** — hierarquia: pai roxo/azul forte → filho mesma família mais claro → neto mais discreto; **semântica de estado sobrepõe**: concluído verde, atrasado vermelho, em risco amarelo/laranja; marco = losango/triângulo, alarme amarelo, evento cinza/azul. (Hoje `_draw_bar` usa `get_status_color` por status; falta a família por nível e estados derivados.)
3. **Linguagem visual consistente** — legenda única: `▲` alarme · `●` evento · `◆` marco · `│` hoje; **objetos clicáveis abrem diálogo de detalhe** (ex.: card de alarme com título/data/relacionado/severidade/status/botão `[Abrir alarme]`).
4. **Linha "Hoje" mais proeminente** + etiqueta `HOJE · 20 AGO` (hoje há só a linha azul 2px).
5. **Resumo na tarefa pai** — `3 tarefas · 0 concluídas · 1 em andamento · 2 atrasadas` ou `45% 3/6` (contagens por estado na linha do pai).

### Fase 1 – Hierarquia
- Expandir/recolher: já existe (árvore + `itemExpanded/Collapsed` → `_update_visible_items`)
- Indentação + prefixo `└─`: já existe (cores por profundidade na árvore)
- **Linha vertical conectando pai↔filhos** (novo): guia visual de parentesco no painel esquerdo
- **Pai como resumo**: linha de resumo agregado (ajuste 1 + 5); barra do pai deve ocupar o span inteiro das filhas com visual de "soma" (mais larga/preenchida, não tracejado fino)
- Progresso agregado do pai: já existe (`TimelineAggregation` + mapper `done/total`)

### Fase 2 – Timeline (canvas)
- Tarefa (barra), período, marco (losango), evento (círculo), alarme (triângulo): **já desenhados** no `TimelineCanvas`
- Linha Hoje: ajuste 4 (prominence + etiqueta)
- Tooltip: já existe (eventos/alarmes primeiro, depois barras) — revisar conteúdo
- **Seleção** (novo): hoje a árvore é `NoSelection`; adicionar seleção da linha ao clicar (destacar barra + linha da árvore)

### Fase 3 – Estados (semântica de cor)
- Estados explícitos atuais: Pendente, Em Andamento, Pausado, Aguardando, Bloqueado, Concluído (theme `STATUS_COLORS`)
- **Estados derivados a calcular** no mapper: `ATRASADA` (end < hoje e não Concluída), `EM RISCO` (prazo próximo / progresso baixo), `NÃO INICIADA` (sem início)
- Paleta por significado (ajuste 2): hierarquia (família de cor por nível) × estado (verde/vermelho/amarelo-laranja); marco sempre distinto
- Linguagem visual consolidada (ajuste 3): legenda única ▲ ● ◆ │

### Fase 4 – Interação
- Clique tarefa → detalhes: **duplo clique já abre** (`open_task_detail_signal`); adicionar clique único → seleção + painel/abrir
- Clique alarme → abre `AlarmPopupQt`/detalhe do alarme (card com título/data/relacionado/severidade/status/`[Abrir alarme]`)
- Clique marco → abre a tarefa-marco
- **Arrastar barra → alterar prazo** (novo; persistir via task service)
- **Redimensionar barra → alterar início/fim** (novo)
- Expand/recolher, zoom Dia/Semana/Mês, Ir para Hoje: já existem na toolbar

### Arquitetura (manter)
- **Custom painting com `QPainter`/`paintEvent`** — NÃO criar dezenas de QWidgets para itens da timeline (padrão já seguido em `TimelineCanvas`)
- Estrutura: `TimelineViewQt` | painel esquerdo árvore de tarefas (`QTreeWidget` como hierarquia) + `TimelineHeader` + `TimelineCanvas` (direita), scroll vertical sincronizado, `h_scrollbar` custom
- Datas derivadas de manual vs agregadas já distinguidas em `TimelineItem` (`manual_start/end` vs `start/end`) — usar para traço (manual) vs barra de resumo (agregado)

### Restrições
- Não adicionar componentes/toolbars novas só por estética; priorizar semântica visual
- Não alterar regras de negócio (datas, agregação, persistência de drag/resize deve passar pelos serviços existentes)
- Não alterar a estrutura de pastas `gui/components/timeline/` sem necessidade

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
- **Banco do projeto (`database/novo_cerebro.db`) é cópia do banco instalado real** (schema v21, migrations 1-21 idênticas, inclui resquícios de teste). Backup original: `database/novo_cerebro.db.bak_20260807_175806`. `ensure_seed_db()` não sobrescreve banco existente; `run_migrations()` aplica só versões novas. Migrações validadas por simulação sobre cópia, sem tocar no instalado (`%LOCALAPPDATA%\CentralGestao`)
- **Resquícios de teste em agregações por FK** (Agenda Geral, etc.): itens órfãos apontando para projeto/tarefa excluídos geravam abas fantasma ("projeto 2", "outro projeto teste", "para testar Eventos"). Regra: validar `is_archived`/`deleted_at` da entidade pai ANTES de criar sub-aba/agrupamento (helper `_project_active`). Não confiar só no filtro interno do widget — a aba é criada antes dele filtrar
- **Não duplicar arg posicional + keyword num helper**: `_rebuild_project_tabs(..., project_repo, kind="events", ..., project_repo=project_repo)` lança `TypeError: got multiple values for argument`. Ao encaminhar kwargs, remover o dup

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

5. **Build EXE + Installer** (CLI oficial; `scripts\build\build_release.py` direto também funciona — os prints `[DEPRECATED]` foram removidos porque o painel delega a esses mesmos scripts):
   ```powershell
   .\venv_build\Scripts\python.exe scripts\ops\control_panel.py build --release
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
