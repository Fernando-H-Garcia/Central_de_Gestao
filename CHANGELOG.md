# Changelog

Todas as mudanças notáveis do Central de Gestão.

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento semântico, com `MAJOR = 0` (pré-1.0).

---

## [Não publicado]

Branch `feature/design-system-refactor`. Ainda não há tag nem instalador
publicado para este bloco.

### Added
- **Janela de Prazos Estimados refatorada** (`gui/dialogs_qt/deadline_dialog_qt.py`)
  - `DeadlineListDialog`: `PageHeader` com "+ Novo Prazo" no topo direito,
    lista, menu de contexto (Editar Prazo / Excluir / + Novo Prazo), botão
    Fechar e estado vazio
  - `DeadlineEditDialog`: Descrição e Data (nessa ordem), com Salvar e Cancelar
  - Marcador da timeline: duplo clique abre o formulário de edição;
    botão direito → "Editar Prazos" abre a lista da tarefa
- **Suítes de teste** (`tests/`): 15 suítes, incluindo 4 de prazos
  Estimados com trava de segurança contra escrita no banco de desenvolvimento

### Fixed
- Menu de contexto dos prazos abria **longe do cursor** — a posição era
  convertida para global duas vezes (`mapToGlobal` aplicado em `popup_at` e
  antes da chamada). Medido: delta 0,0 px
- Fechar a janela de prazos **abria "Novo Prazo" sozinho** — o roteamento
  abria a lista e só depois do `exec()` aparecia o formulário
- Abrir "Editar Prazo" preenchia a data com **hoje** em vez da data do
  prazo, sobrescrevendo a data ao salvar
- Campos do formulário ficavam **invisíveis**: `Card` já nasce com layout
  próprio e o Qt recusa `setLayout()` quando já existe um

### Changed
- Documentação reorganizada: 72 → 28 documentos. Removidos 43 arquivos finos
  e duplicados, e consolidados os fatos em 8 documentos substantes
- ADR-011 criado (one-file) e ADR-003 marcado como superado
- ADRs e BUGs corrigidos onde registravam a versão do Python invertida
  (3.12 → 3.11), `build/build.spec` inexistente e `brain.db` inexistente

---

## [0.8.1] - 2026-09-15

### Added
- Renomear anexo na Documentação (botão direito, preserva extensão)

---

## [0.8.0]

### Added
- Estrutura de documentação (`docs/`)
- Pipeline de CI unificada (GitHub Actions)
- Script único de build (`scripts/build/build_release.py`)
- Smoke test automático (`scripts/tests/smoke_test.py`)
- Build Contract documentado
- Sistema de versão única (`scripts/build/version.py`)
- Release automation (`scripts/release/create_release.py`)
- Validação de instalador (`scripts/tests/validate_installer.py`)
- Bump de versão (`scripts/build/bump_version.py`)
- CHANGELOG.md
- Regras proibidas (Hard Rules) na composição do projeto

### Fixed
- `.gitignore`: `build/` → `/build/`, para não ignorar `scripts/build/`

### Changed
- Workflow do CI passou a chamar `build_release.py` como comando único
- `installer.iss`: versão passada via `/DMyAppVersion`
- Processo de release documentado em 4 fases obrigatórias

---

## [0.7.0]

### Added
- Interface completa em PySide6/Qt6
- Módulos: Projetos, Tarefas, Ideias, Wiki, Agenda, Alarmes
- Sistema de migrations SQL
- EventBus para comunicação entre views
- BadgeDelegate para status e prioridade
- WikiTextEdit com autocomplete `[[` e `{{`
- Activity Summary
- Sistema de referências entre entidades

### Fixed
- Segfault do BadgeDelegate (delegates criados sem dono)
- DLL mismatch no bundle (ambiente Conda)
- Wiki: parent combo, drag-drop, label "Tamanho:"
- Tarefas que não apareciam após criação
- Ideias que não eram salvas
- Promote de ideias quebrado

### Changed
- Autosave removido da wiki (conflitava com "Descartar")
- EventBus refatorado (QTimer persistente)
- Sidebar redesign

---

## [0.6.0]

### Added
- Primeira versão funcional
- Pipeline de build PyInstaller
- Instalador Inno Setup
- SQLite com migrations
- Estrutura de repositórios e serviços

---

## Nota sobre datas

Os ADRs e BUGs sob `docs/` têm datas de **2024**, quando a documentação foi
gerada em bloco. O trabalho real começou em 2026. Cada documento afetado traz
uma "Nota de revisão (2026-10)" indicando as correções. Ver
[`docs/README.md`](docs/README.md).