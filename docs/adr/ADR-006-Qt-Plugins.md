# ADR-006: Gerenciamento de Qt Plugins

**Data**: 2024-03-15
**Status**: Vigente, com ressalva

> **Nota de revisão (2026-10):** ver a ressalva no final.

## Contexto
O PyInstaller não inclui automaticamente todos os plugins Qt necessários.

## Decisão
Declarar explicitamente no spec os plugins usados:
`platforms`, `sqldrivers`, `styles`, `imageformats`.

## Consequências
- App funciona sem Qt instalado no PC do usuário
- Bundle não carrega traduções nem plugins não usados

## Ressalva (2026-10)

A parte do registro original sobre **"38 DLLs `api-ms-win-*` removidas"** já
não se aplica da mesma forma:

- O `cleanup_dlls.py` existe apenas como **template**
  (`scripts/build/templates/cleanup_dlls.py`) e **não é executado** pelo
  `build_release.py`.
- Isso é consequência direta da mudança para **one-file**
  (ver [ADR-011](ADR-011-OneFile.md)): no modo one-file o PyInstaller resolve
  as DLLs do próprio Qt, e o bundle final é um único `.exe` de 46,1 MB.

Se um dia o build voltar a gerar `_internal/` com DLLs duplicadas, o
`cleanup_dlls.py` é o ponto de partida — mas antes disso, confirme que o spec
não regredeu para one-folder.

Verificação rápida de que a lista de plugins está correta: o EXE compila e
abre sem `could not find or load the Qt platform plugin`.