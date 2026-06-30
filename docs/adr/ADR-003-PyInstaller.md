# ADR-003: Empacotamento com PyInstaller

**Data**: 2024-01-20

## Contexto
Distribuir app desktop Python sem exigir Python no PC do usuário.

## Decisão
PyInstaller em modo one-folder. Spec centralizado em `build/build.spec`.

## Consequências
- Bundle de ~300 MB
- DLLs problemáticas exigem cleanup manual
- UPX reduz tamanho
