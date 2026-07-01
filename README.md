# Central de Gestão

Sistema desktop para gerenciamento de projetos, tarefas, ideias, notas, documentação wiki e agenda pessoal.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![PySide6](https://img.shields.io/badge/PySide6-6.6-green) ![SQLite](https://img.shields.io/badge/SQLite-3-orange)

## Funcionalidades

- **Projetos** — Cadastro, edição, exclusão com análise de impacto
- **Tarefas** — CRUD completo, dependências, alarmes, atividade logging
- **Wiki** — Documentação com formatação Markdown, links entre páginas, autocomplete `[[` e `{{`
- **Agenda** — Eventos, alarmes recorrentes, calendário
- **Ideias** — Captura rápida, promoção para tarefa/projeto
- **Notas** — Anotações rápidas
- **Resumo de Atividades** — Histórico agrupado por projeto/tarefa com links clicáveis

## Instalação

Baixe o instalador mais recente da página de [Releases](https://github.com/Fernando-H-Garcia/Central_de_Gestao/releases) e execute.

O programa será instalado em `Program Files\Central de Gestão` e os dados do usuário ficam em `%LOCALAPPDATA%\CentralGestao\`.

## Build

```bash
cd build
python -m PyInstaller build.spec --clean --noconfirm
# Opcional: gerar instalador com Inno Setup
ISCC.exe installer.iss
```

## Documentação

A documentação completa está em [`docs/`](docs/README.md):
- [`docs/engineering/`](docs/engineering/) — 32 documentos técnicos (arquitetura, build, deploy, etc.)
- [`docs/adr/`](docs/adr/) — Architecture Decision Records
- [`docs/bugs/`](docs/bugs/) — Registro de bugs e correções

## Tecnologias

- **GUI:** PySide6 (Qt6)
- **Banco:** SQLite com migrations versionadas
- **Build:** PyInstaller (one-folder) + Inno Setup
- **Arquitetura:** 5 camadas (GUI → Services → Repositories → Models → Database), EventBus, Repository pattern

## Versão

Atual: **v0.8.0** — [CHANGELOG](CHANGELOG.md)

## Licença

MIT License — Fernando H. Garcia
