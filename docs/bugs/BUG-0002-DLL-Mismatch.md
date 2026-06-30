# BUG-0002: DLL Mismatch no Bundle

**Status**: Corrigido
**Data**: 2024-03-12

## Sintoma
App compilado com Conda apresentava erro de DLL Qt ao abrir.

## Causa
Ambiente Conda usava Python 3.11.5 + PySide6 6.11.1, mas DLLs do bundle eram de versão incompatível.

## Solução
Build feito com Python 3.12.1 (non-Conda) + PySide6 6.6.3.1.
