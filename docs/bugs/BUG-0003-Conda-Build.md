# BUG-0003: Conda Build Quebrado

**Status**: Corrigido
**Data**: 2024-03-12

## Sintoma
PyInstaller com ambiente Conda produzia bundle com erro de inicialização.

## Causa
Conda gerencia bibliotecas de forma diferente. PySide6 6.11.1 do Conda não é compatível com o runtime empacotado.

## Solução
Ambiente oficial: Python 3.12.1 puro + PySide6 6.6.3.1 (pip, não Conda).
