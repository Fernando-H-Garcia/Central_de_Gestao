# Ambiente e Estrutura

Referência do ambiente oficial de build e da organização de pastas do
repositório. Verificado em **2026-10-13**.

## Ambiente oficial

| Item | Versão | Nota |
|---|---|---|
| **Python** | **3.11.5** | **3.12+ quebra o PySide6 6.6** |
| PySide6 | 6.6.3.1 | faixa `>=6.6,<6.7`; 6.11+ falha no 3.11 |
| Qt | 6.6.3 | acompanha o PySide6 |
| PyInstaller | 6.21.0 | faixa `>=6.21,<7.0` |
| Inno Setup 6 | 6.4+ | `C:\Program Files (x86)\Inno Setup 6\` |
| Windows | 10/11 | |

> ⚠️ **A versão do Python é 3.11, não 3.12.** Documentos antigos diziam 3.12 e
> estavam errados — ver [BUG-0002](bugs/BUG-0002-DLL-Mismatch.md).

⚠️ **`build_release.py` ainda emite um aviso enganoso:**
`[AVISO] Versao Python: 3.11.5 (esperado 3.12)`. O valor esperado no script
está invertido. Não "corrija" o Python por causa desse aviso — vai quebrar o
build. (Pendente de correção.)

### Ambiente de build

O venv de build fica em `venv_build/` (gitignored) e **não** deve ser
confundido com o Python do sistema:

```powershell
.\venv_build\Scripts\python.exe -c "import PySide6; from PySide6 import QtCore; print(PySide6.__version__, QtCore.qVersion())"
```

Detalhe do Conda: ele serve **apenas** para criar o venv
(`C:\Anaconda\python.exe -m venv venv_build`). Depois disso use sempre
`venv_build\Scripts\pip.exe` e `venv_build\Scripts\python.exe`.

Procedimento completo em [`BUILD.md`](BUILD.md).

## Estrutura de pastas

```
Central_de_Gestão/
├── core/          # event_bus, data_context, refresh_manager
├── database/      # connection.py, migrations/, repositories/
├── gui/           # interface (Qt6)
│   ├── components/    # componentes reutilizáveis (buttons, card, timeline…)
│   ├── dialogs_qt/    # diálogos
│   ├── views/         # telas
│   └── widgets/       # widgets reutilizáveis (TitleEdit, WikiTextEdit)
├── models/        # entidades do domínio
├── services/      # lógica de negócio
├── scripts/       # build, release, guards, hooks, ops
├── tests/         # suítes de teste (ver Testes.md)
├── docs/          # esta documentação
├── utils/         # instrumentação, paths
├── config/        # default_config.json
├── attachments/   # anexos
├── logs/          # logs de runtime
├── main.py
├── config.py
├── CentralDeGestao.spec
└── venv_build/    # ambiente de build (gitignored)
```

Diretórios que **não** existem mais (removidos na limpeza de código morto):
`plugins/`, `data/`, `scratch/`, e o `dist/` antigo na raiz.

## Configuração

`config/default_config.json` é o padrão embarcado. O usuário pode sobrescrever
em `%LOCALAPPDATA%\CentralGestao\config\`.

Ver [ADR-008](adr/ADR-008-Config.md).

## Onde ficam os dados do usuário

| Dado | Caminho |
|---|---|
| Banco | `%LOCALAPPDATA%\CentralGestao\database\novo_cerebro.db` |
| Config | `%LOCALAPPDATA%\CentralGestao\config\` |
| Logs | `%LOCALAPPDATA%\CentralGestao\logs\` |
| Backups | `%LOCALAPPDATA%\CentralGestao\backups\` |
| Anexos | `~/Documents/Central de Gestão/Anexos/` |
| Seed (empacotado) | `_internal/database/novo_cerebro.db` |

Motivo de o banco ficar fora de `Program Files`: a pasta de instalação é
read-only para o usuário. Ver [ADR-002](adr/ADR-002-LOCALAPPDATA.md).

### Logs que importam na diagnose

| Arquivo | Quando olhar |
|---|---|
| `%LOCALAPPDATA%\CentralGestao\logs\boot.log` | App não abre / não pinta |
| `%LOCALAPPDATA%\CentralGestao\logs\app_errors.log` | Exceções em runtime |

Erros são **datados**. Ao investigar, confira a data antes de culpar a mudança
atual — o `app_errors.log` guarda histórico.

## Backup

O banco é um arquivo único: copiar `novo_cerebro.db` é o backup inteiro.

Antes de um build, fazer backup do banco do repositório e guardar o SHA-256:

```powershell
Copy-Item database\novo_cerebro.db backups\pre_build.db
(Get-FileHash database\novo_cerebro.db -Algorithm SHA256).Hash
```

> O banco do repositório é de desenvolvimento e **não é versionado de forma
> confiável**. Sempre verifique o hash depois de rodar build ou testes.

`backups/` é gitignored — é cópia de runtime, nunca entra no repositório.