# Central de Gestão

Sistema desktop para gerenciamento de projetos, tarefas, ideias, notas,
documentação wiki e agenda pessoal.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![PySide6](https://img.shields.io/badge/PySide6-6.6-green) ![Qt](https://img.shields.io/badge/Qt-6.6-green) ![SQLite](https://img.shields.io/badge/SQLite-orange)

## Funcionalidades

- **Projetos** — cadastro, edição, exclusão com análise de impacto
- **Tarefas** — CRUD completo, subtarefas com árvore, dependências, alarmes
- **Planning** — timeline/Gantt com barra arrastável, zoom contínuo e
  **prazos estimados** com marcadores e alarmes automáticos
- **Wiki** — Markdown, links entre páginas, autocomplete `[[` e `{{`
- **Agenda** — eventos, alarmes e calendário com dia atual destacado
- **Ideias** — captura rápida, promoção para tarefa/projeto
- **Notas** — anotações rápidas
- **Resumo de Atividades** — histórico agrupado por projeto/tarefa, com
  seções recolhíveis e links clicáveis

## Instalação

Baixe o instalador mais recente da página de
[Releases](https://github.com/Fernando-H-Garcia/Central_de_Gestao/releases) e
execute.

O programa é instalado em `Program Files\Central de Gestão`; os dados do
usuário ficam em `%LOCALAPPDATA%\CentralGestao\` e sobrevivem à desinstalação.

## Build

```powershell
.\venv_build\Scripts\python.exe scripts\ops\control_panel.py build --release
```

Ambiente obrigatório: **Python 3.11**, PySide6 6.6.x, PyInstaller 6.21+.
Procedimento completo, incluindo criação do venv, em [`docs/BUILD.md`](docs/BUILD.md).

| Artefato | Tamanho |
|---|---|
| `build\dist\CentralDeGestao.exe` | ~46 MB (one-file) |
| `build\CentralDeGestao_Installer.exe` | ~70 MB |

## Documentação

Comece por [`docs/README.md`](docs/README.md).

| Onde | O quê |
|---|---|
| [`docs/Arquitetura.md`](docs/Arquitetura.md) | Camadas, fluxo de boot, banco, Qt |
| [`docs/BUILD.md`](docs/BUILD.md) | Como compilar |
| [`docs/Release.md`](docs/Release.md) | Como publicar uma versão |
| [`docs/Testes.md`](docs/Testes.md) | Suítes e regras de isolamento de banco |
| [`docs/Composicao-do-Projeto.md`](docs/Composicao-do-Projeto.md) | Regras que não podem ser quebradas |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`docs/bugs/`](docs/bugs/) | Registro de bugs e correções |

`AGENTS.md` na raiz traz as regras para agentes de IA e o histórico de
aprenderizados do projeto.

## Tecnologias

- **GUI:** PySide6 6.6 / Qt 6.6
- **Banco:** SQLite com migrations versionadas (25 arquivos, schema v26)
- **Build:** PyInstaller (one-file) + Inno Setup 6
- **Arquitetura:** camadas `GUI → Services → Repositories → Models → Database`,
  EventBus para comunicação entre views, Repository pattern

## Versão

Atual: **0.8.1** — [CHANGELOG](CHANGELOG.md)

## Licença

MIT License — Fernando H. Garcia