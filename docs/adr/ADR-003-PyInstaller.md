# ADR-003: Empacotamento com PyInstaller

**Data**: 2024-01-20
**Status**: **Superado** — ver [ADR-011](ADR-011-OneFile.md)

## Contexto
Distribuir o app desktop Python sem exigir Python instalado no PC do usuário.

## Decisão (original)
PyInstaller em modo **one-folder**. Spec centralizado em `build/build.spec`.

## Consequências (originais)
- Bundle de ~300 MB
- DLLs problemáticas exigiam cleanup manual
- UPX reduzia tamanho

---

## Correção (2026-10)

Esta ADR está **superada**. Os três pontos acima descrevem uma realidade que o
projeto não tem mais:

| ADR original | Realidade atual |
|---|---|
| Modo **one-folder** | Modo **one-file** (ver ADR-011) |
| Spec em `build/build.spec` | Spec em **`CentralDeGestao.spec`**, na raiz do repositório |
| Bundle de ~300 MB | EXE único de **46,1 MB** |

O motivo da troca está registrado em [ADR-011-OneFile](ADR-011-OneFile.md).

A data original (2024-01-20) foi preservada por ser um registro histórico; ver
[`docs/README.md`](../README.md) sobre a política de datas.