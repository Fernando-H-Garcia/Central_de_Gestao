# Build — Central de Gestão

Guia definitivo para gerar o executável e o instalador.

## Pré-requisitos

| Item | Versão | Notas |
|---|---|---|
| Python | **3.11** | 3.12+ quebra compatibilidade com PySide6 |
| PySide6 | **>=6.6, <6.7** | 6.11+ falha com `DLL load failed` no Python 3.11 |
| PyInstaller | **>=6.21, <7.0** | |
| Inno Setup 6 | 6.4+ | Instalar em `C:\Program Files (x86)\Inno Setup 6\` |
| `VC_redist.x64.exe` | opcional | Colocar na raiz do projeto |

## Setup (uma vez)

```powershell
# 1. Criar ambiente virtual com Python 3.11
& "C:\Anaconda\python.exe" -m venv venv_build

# 2. Instalar dependências com versões corretas (CRÍTICO)
.\venv_build\Scripts\pip.exe install "PySide6>=6.6,<6.7" "pyinstaller>=6.21,<7.0" Markdown>=3.5

# 3. Verificar compatibilidade
.\venv_build\Scripts\python.exe -c "import PySide6; from PySide6 import QtCore; print(f'PySide6: {PySide6.__version__}, Qt: {QtCore.qVersion()}')"
```

Esperado: `PySide6: 6.6.x, Qt: 6.6.x`

## Build

### ⚠️ Antes de buildar — banco de seed limpo

O instalador embala `database/novo_cerebro.db` como seed. **Nunca faça o build com o banco de produção**, senão o instalador distribuirá seus dados reais.

Gere um banco vazio (schema puro, sem dados) antes de buildar:

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

Depois do build, restaure o banco original:

```powershell
Move-Item database\novo_cerebro.db.bak database\novo_cerebro.db -Force
Remove-Item database\seed_empty.db -ErrorAction SilentlyContinue
```

### Buildar

```powershell
.\venv_build\Scripts\python.exe scripts\build\build_release.py --release
```

### Artefatos

| Arquivo | Tamanho | Descrição |
|---|---|---|
| `build\dist\CentralDeGestao.exe` | ~46 MB | Executável one-file, self-contained |
| `build\CentralDeGestao_Installer.exe` | ~70 MB | Instalador Inno Setup (inclui VC++ Redist) |

### Copiar para distribuição

```powershell
Copy-Item build\CentralDeGestao_Installer.exe ..\Executaveis\ -Force
```

## Arquitetura do build

- **Spec**: `CentralDeGestao.spec` na raiz — `console=False`, `icon='app.ico'`, **one-file mode**
- **Modo one-file** (sem COLLECT): EXE inclui `a.binaries + a.zipfiles + a.datas` — tudo num único arquivo
- **Logs**: gravados em `%LOCALAPPDATA%\CentralGestao\logs\boot.log` com timestamp por etapa
- **Dados**: `%LOCALAPPDATA%\CentralGestao\` (DB, config, logs, backups, anexos)
- **Processo único**: apenas `subprocess.Popen(["explorer", ...])` para abrir arquivos no Windows Explorer

## Instrumentação de boot

O `main.py` registra sequencialmente no `boot.log`:

```
[BOOT] início do main
[BOOT] configurações carregadas
[BOOT] migrations/banco executados
[BOOT] QApplication criada
[BOOT] MainWindow instanciada
[BOOT] MainWindow.show() chamado
[BOOT] app.exec() iniciado
```

E o `MainWindow.showEvent()` confirma visibilidade real + `paintEvent()` confirma renderização.

## Troubleshooting

| Sintoma | Causa | Solução |
|---|---|---|
| `DLL load failed while importing QtWidgets` | PySide6 6.11+ no Python 3.11 | `pip install "PySide6>=6.6,<6.7"` |
| EXE com 2.5 MB | Spec em one-folder (COLLECT) | Remover COLLECT; EXE deve incluir `a.binaries, a.zipfiles, a.datas` |
| `PERFORMANCE_DEBUG = True` causa I/O excessivo | Setar `False` em `utils/instrumentation.py:4` |
| App crasha escrevendo logs em `Program Files` | `LOGS_DIR` apontando para lugar errado | Verificar `config.py` — usar `data_root()` → `%LOCALAPPDATA%\CentralGestao\logs\` |
| App não abre janela | Erro silencioso | Checar `%LOCALAPPDATA%\CentralGestao\logs\boot.log` |
