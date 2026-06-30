# Build Contract

Este documento define o **contrato de saída do build**: o que o script `scripts/build/build_release.py` deve produzir e quais critérios determinam se um build é válido.

## Arquivos obrigatórios

```
build/dist/CentralDeGestao/
├── CentralDeGestao.exe          # Executável principal
├── _internal/
│   ├── database/
│   │   └── migrations/          # 20 arquivos .sql
│   ├── config/
│   │   └── default_config.json
│   ├── attachments/
│   │   └── sort_icon.png
│   ├── PySide6/
│   │   └── plugins/
│   │       ├── platforms/       # qwindows.dll
│   │       ├── sqldrivers/      # qsqlite.dll
│   │       ├── styles/          # qmodernstyle.dll, qwindowsvistastyle.dll
│   │       └── imageformats/    # qico, qjpeg, qpng, qsvg, qtiff, etc.
│   └── shiboken6/               # shiboken6.abi3.dll
```

## Critérios de sucesso

| Critério | Regra |
|----------|-------|
| Executável existe | `CentralDeGestao.exe` presente em `dist/CentralDeGestao/` |
| Tamanho mínimo | EXE ≥ 30 MB (bundle completo ≈ 250-350 MB) |
| `_internal/` existe | Diretório presente com todos os subdiretórios |
| Plugins Qt carregam | `platforms`, `sqldrivers`, `styles`, `imageformats` presentes |
| Shiboken presente | `shiboken6/` com `shiboken6.abi3.dll` |
| Migrations copiadas | `database/migrations/` com todos os .sql |
| Config copiada | `config/default_config.json` presente |
| SQLite inicializa | App abre sem erro de banco |
| Sem crash no startup | Smoke test passa (15s sem crash) |

## O que o script `build_release.py` DEVE fazer

1. Validar ambiente (Python 3.12, PySide6 6.6, PyInstaller)
2. Limpar artefatos anteriores
3. Executar PyInstaller com `build/build.spec`
4. Remover DLLs obsoletas (`api-ms-win-*`, `ext-ms-win-*`)
5. Validar TODOS os critérios acima
6. Gerar `build/build_report.txt` com resultados
7. Se `--release`: gerar instalador Inno Setup
8. **Exit code 0** se tudo OK, **exit code 1** se falhar

## O que o CI DEVE fazer

1. Chamar `python scripts/build/build_release.py` (comando ÚNICO)
2. Chamar `python scripts/tests/smoke_test.py` para validar execução real
3. Subir artefato `dist/CentralDeGestao/` para download

## Regras de execução

- ❌ NENHUM build manual fora de `build_release.py`
- ❌ NENHUM PyInstaller chamado diretamente
- ❌ NENHUM passo de build duplicado no CI
- ✅ TODO build → `python scripts/build/build_release.py`
- ✅ TODO release → `python scripts/build/build_release.py --release`
