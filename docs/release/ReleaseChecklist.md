# Release Checklist

Checklist obrigatório para toda release. Nenhum item pode ficar em branco.

## Fase 1: Preparação

### Versionamento
- [ ] Versão atualizada no `build/installer.iss` (`MyAppVersion`)
- [ ] Tag semântica definida (v0.x.y)

### Ambiente
- [ ] Python 3.12.1 (puro, não Conda) — `python --version`
- [ ] PySide6 6.6.3.1 — `python -c "import PySide6; print(PySide6.__version__)"`
- [ ] PyInstaller 6.21.0 — `python -c "import PyInstaller; print(PyInstaller.__version__)"`
- [ ] Nenhuma dependência extra instalada no ambiente

### Código
- [ ] `python -m py_compile main.py` — sem erros
- [ ] `python -m py_compile config.py` — sem erros
- [ ] `python check_schema.py` — migrations consistentes
- [ ] Último commit revisado e testado

## Fase 2: Build

### Execução
- [ ] `python scripts/build/build_release.py` executa sem erros
- [ ] PyInstaller completa sem warnings críticos
- [ ] DLLs obsoletas removidas (api-ms-win-*, ext-ms-win-*)
- [ ] Plugins Qt validados (platforms, sqldrivers, styles, imageformats)

### Artefatos
- [ ] `build/dist/CentralDeGestao/CentralDeGestao.exe` existe (~50-80 MB)
- [ ] `build/CentralDeGestao_Installer.exe` gerado (~100 MB)
- [ ] Pasta `_internal/` completa com PySide6, shiboken6, plugins, migrations

## Fase 3: Validação

### Instalação
- [ ] Instalador executa em máquina Windows sem Python
- [ ] Instala em `C:\Program Files\Central de Gestão`
- [ ] Atalho no Menu Iniciar criado
- [ ] Aplicação abre sem erros
- [ ] Console não exibe tracebacks

### Fluxo crítico
- [ ] Sidebar navega entre todas as telas
- [ ] Projetos: criar, editar, arquivar, restaurar
- [ ] Tarefas: criar, editar, deletar
- [ ] Ideias: criar, promover para projeto/tarefa
- [ ] Wiki: criar página, editar, salvar, links [[ e {{ funcionam
- [ ] Agenda: eventos, alarmes disparam
- [ ] Atividades: log é gerado e filtros funcionam
- [ ] Anexos: upload por drag-drop e botão

### Dados
- [ ] Banco SQLite criado em `%LOCALAPPDATA%\CentralGestao\brain.db`
- [ ] Migrations executadas (20 migrations)
- [ ] Dados de seed carregados
- [ ] Anexos salvos em `~/Documents/Central de Gestão/Anexos/`

### Desinstalação
- [ ] Desinstalação remove arquivos do programa
- [ ] Dados em `%LOCALAPPDATA%` preservados
- [ ] Reinstalação reconhece dados existentes

## Fase 4: Publicação

### Git
- [ ] Tag criada: `git tag -a v0.x.y -m "Release v0.x.y"`
- [ ] Tag enviada: `git push origin v0.x.y`

### GitHub
- [ ] Release criado em https://github.com/Fernando-H-Garcia/Central_de_Gestao/releases
- [ ] `CentralDeGestao_Installer.exe` anexado ao release
- [ ] Nota de versão escrita com:
  - Novas funcionalidades
  - Bugs corrigidos
  - Breaking changes (se houver)
  - Ambiente oficial usado no build

### Pós-release
- [ ] CHANGELOG.md atualizado (se existir)
- [ ] Issues fechadas relacionadas à versão

## Assinatura

```
Release Manager: __________________
Data: ____________________________
Versão: __________________________
```
