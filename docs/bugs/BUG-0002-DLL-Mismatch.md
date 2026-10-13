# BUG-0002: DLL Mismatch no Bundle

**Status**: Corrigido
**Data**: 2024-03-12

> **Nota de revisão (2026-10):** a "solução" original está com a versão do
> Python **invertida**. Ver a correção no final.

## Sintoma
App compilado com Conda apresentava erro de DLL do Qt ao abrir.

## Causa
O ambiente Conda trazia PySide6 6.11.1, cujos binários não são compatíveis
com o runtime empacotado.

## Solução (original, incorreta)
> Build feito com **Python 3.12.1** (non-Conda) + PySide6 6.6.3.1.

## Correção (2026-10)

O Python correto é **3.11**, não 3.12. O registro original inverteu a regra:

- **PySide6 6.6.x só funciona em Python ≤ 3.11.**
- Em Python 3.12+ o PySide6 6.6 falha com
  `DLL load failed while importing QtWidgets`.

Ambiente oficial correto (medido em 2026-10-13):

| Item | Versão |
|---|---|
| Python | **3.11.5** |
| PySide6 | 6.6.3.1 |
| Qt | 6.6.3 |
| PyInstaller | 6.21.0 |

Este erro inverteu-se depois em `build_release.py`, que emite
`[AVISO] Versao Python: 3.11.5 (esperado 3.12)` — um aviso **errado** que
pode induzir alguém a "consertar" o Python e quebrar o build. Ainda não
corrigido (verificado em 2026-10-13).