# Release

Este documento define o processo oficial de geração de uma versão do Central de Gestão.

## Fluxo completo de release

### Fase 1: Preparação

1. **Atualizar versão no `build/installer.iss`**
   - `#define MyAppVersion "0.x"`
   - Commit: `bump version to 0.x`

2. **Atualizar `scripts/release/version.txt`** (se existir)

3. **Verificar ambiente oficial**
   - Python 3.12.1 (puro, não Conda)
   - PySide6 6.6.3.1
   - PyInstaller 6.21.0

4. **Executar testes básicos**
   ```bash
   python -m py_compile main.py
   python check_schema.py
   ```

### Fase 2: Build

5. **Rodar build script unificado**
   ```bash
   python scripts/build/build_release.py
   ```
   Este script executa automaticamente:
   - Limpeza de artefatos anteriores
   - PyInstaller (via `build/build.spec`)
   - Remoção de DLLs obsoletas (`cleanup_dlls.py`)
   - Validação de plugins Qt
   - Geração do instalador Inno Setup

6. **Validar saída do build**
   - `build/dist/CentralDeGestao/` existe
   - `build/CentralDeGestao_Installer.exe` gerado
   - Tamanho do instalador (~100 MB)

### Fase 3: Validação

7. **Instalar em máquina limpa**
   - Executar instalador em Windows sem Python
   - Verificar instalação em `C:\Program Files\Central de Gestão`
   - Verificar dados em `%LOCALAPPDATA%\CentralGestao\`

8. **Testar fluxo crítico**
   - App abre sem erros
   - Sidebar navega
   - Criar projeto + tarefa + ideia
   - Wiki edita e salva
   - Alarmes funcionam
   - Anexos são carregados
   - Desinstalação limpa (dados preservados)

### Fase 4: Publicação

9. **Publicar release no GitHub**
   ```bash
   python scripts/release/create_tag.py 0.x
   ```
   - Criar release em https://github.com/Fernando-H-Garcia/Central_de_Gestao/releases
   - Anexar `CentralDeGestao_Installer.exe`
   - Escrever nota de versão com:
     - Novas funcionalidades
     - Bugs corrigidos
     - Checklist de homologação

## Rollback

Se a validação falhar:
1. Identificar se o problema é de código ou de build
2. Se for build: ajustar script e rebuildar
3. Se for código: corrigir, commitar, rebuildar
4. Nunca liberar versão com checklist incompleto
