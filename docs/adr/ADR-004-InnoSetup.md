# ADR-004: Instalador com Inno Setup

**Data**: 2024-01-20
**Status**: Vigente

> **Nota de revisão (2026-10):** registro escrito em 2024. Correções
> factuais ao final. Ver [`docs/README.md`](../README.md).

## Contexto
PyInstaller gera o executável. É necessário um instalador Windows que também
instale o VC++ Redistributable.

## Decisão
Inno Setup 6, com o script maintained em
**`scripts/build/templates/installer.iss`** e a versão passada por
`/DMyAppVersion` na linha de comando.

## Consequências
- Instalação simplificada (next, next, finish)
- Remoção via Painel de Controle
- VC++ Redist garante o funcionamento

## Correção factual (2026-10)
- O script **não vive em `build/installer.iss`**. O original está em
  `scripts/build/templates/installer.iss`; o `build_release.py` copia para
  `build/` no momento de gerar o instalador. Editar o arquivo em `build/`
  significa que a mudança se perde no próximo build.
- A versão é injetada em tempo de build:
  ```
  ISCC.exe /DMyAppVersion="0.8" build\installer.iss
  ```
  Não edite a versão dentro do `.iss` — use `scripts/build/version.py`
  (fonte única: `VERSION = "0.8.1"`, `VERSION_SHORT = "0.8"`).
- Tamanho atual do instalador: **70,1 MB** (não ~100 MB; caiu junto com a
  mudança para one-file, ver [ADR-011](ADR-011-OneFile.md)).