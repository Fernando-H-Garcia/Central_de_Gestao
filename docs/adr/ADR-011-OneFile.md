# ADR-011: PyInstaller em Modo One-File

**Data**: 2026-10-13
**Status**: Vigente — substitui [ADR-003](ADR-003-PyInstaller.md)

## Contexto

O projeto empacotava em modo **one-folder** (`dist/CentralDeGestao/` com a pasta
`_internal/`), o que gerava três problemas:

1. **209 MB de artefato** para um app que o usuário executa com um duplo clique.
   A pasta inteira precisa ser copiada e distribuída junto com o `.exe`.
2. **Dois builds-shadow**: o diretório `build/dist/` (oficial) e um `dist/` na
   raiz (resíduo antigo) podiam ser confundidos. O `dist/` na raiz chegou a
   acumular 209 MB de um build obsoleto.
3. O `.exe` ficava *dentro* de uma pasta, o que quebrava atalhos e gerava
   complaints do antivírus por manipulação de arquivos na pasta de instalação.

## Decisão

Empacotar em **modo one-file**, com o spec na **raiz** do repositório
(`CentralDeGestao.spec`), acionado pelo comando único:

```powershell
.\venv_build\Scripts\python.exe scripts\ops\control_panel.py build [--release]
```

No spec one-file, o `EXE` precisa incluir `a.binaries + a.zipfiles + a.datas`.
**Remover o `COLLECT`** — sua presença é exatamente o que faz o PyInstaller
cair de volta para one-folder.

## Consequências

### Positivas
- **46,1 MB** em um único arquivo `.exe`, self-contained.
- Instalador Inno Setup com **70,1 MB** (era ~100 MB).
- Nenhum segundo diretório de saída — elimina a confusão do `dist/` na raiz.
- Copiar para distribuição é `Copy-Item` de um arquivo.

### Negativas
- O executável extrai para uma pasta temporária a cada execução
  (`%TEMP%\_MEIxxxxxx`), o que torna o primeiro carregamento mais lento.
- Antivírus tends a inspecionar o arquivo inteiro na primeira execução.

### Validação (medida em 2026-10-13)
| Artefato | Esperado | Obtido |
|---|---|---|
| `build\dist\CentralDeGestao.exe` | ~46 MB | 46,1 MB |
| `build\CentralDeGestao_Installer.exe` | ~70 MB | 70,1 MB |

O EXE foi executado e não apenas compilado: abriu, pintou e rodou sem erros
(ver `docs/BUILD.md`).

## Como saber se regredi

Se o `build_release.py` reportar **"Single EXE (onefile) - 1 arquivo"** e o
`.exe` tiver menos de ~20 MB, o `COLLECT` voltou. O build ainda passa, mas
silenciosamente entrega one-folder.