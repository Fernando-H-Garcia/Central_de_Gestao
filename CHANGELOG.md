# Changelog

Todas as mudanças notáveis no Central de Gestão serão documentadas aqui.

## [0.8.0] - 2024-06-30

### Added
- Estrutura completa de documentação (docs/engineering/, docs/adr/, docs/bugs/)
- Pipeline CI unificada (GitHub Actions)
- Script único de build (scripts/build/build_release.py)
- Smoke test automático (scripts/tests/smoke_test.py)
- Build Contract documentado (docs/engineering/32-Build-Contract.md)
- Sistema de versão única (scripts/build/version.py)
- Release Automation Script (scripts/release/create_release.py)
- Validação de instalador (scripts/tests/validate_installer.py)
- Bump version script (scripts/build/bump_version.py)
- CHANGELOG.md
- Regras proibidas (Hard Rules) na constituição do projeto

### Fixed
- .gitignore: `build/` → `/build/` para não ignorar `scripts/build/`

### Changed
- workflow do CI: agora chama `build_release.py` como comando único
- `installer.iss`: versão passada dinamicamente via `/DMyAppVersion`
- Processo de release documentado em 4 fases obrigatórias

## [0.7.0] - 2024-03-15

### Added
- Interface completa em PySide6/Qt6
- Módulos: Projetos, Tarefas, Ideias, Wiki, Agenda, Alarmes
- Sistema de migrations (20 migrations SQL)
- EventBus para comunicação entre views
- BadgeDelegate para status e prioridade
- WikiTextEdit com autocomplete [[ e {{
- Activity Summary view
- Sistema de referências entre entidades

### Fixed
- Segfault do BadgeDelegate (parent=None)
- DLL Mismatch no bundle (ambiente Conda)
- Wiki: parent combo, drag-drop, label "Tamanho:"
- Tasks não aparecendo após criação
- Ideias não sendo salvas
- Promote de ideias quebrado

### Changed
- Autosave removido (conflito com "Descartar")
- EventBus refatorado (QTimer persistente)
- Sidebar redesign (280px, sem word wrap)

## [0.6.0] - 2024-01-20

### Added
- Primeira versão funcional
- PyInstaller build pipeline
- Inno Setup installer
- SQLite com migrations
- Estrutura de repositórios e serviços
