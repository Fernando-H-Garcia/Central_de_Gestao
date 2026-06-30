# ADR-006: Gerenciamento de Qt Plugins

**Data**: 2024-03-15

## Contexto
PyInstaller não inclui automaticamente todos os plugins Qt necessários.

## Decisão
Incluir plugins manualmente: platforms, sqldrivers, styles, imageformats. Remover DLLs api-ms-win-*.

## Consequências
- App funciona sem Qt instalado
- 38 DLLs desnecessárias removidas
