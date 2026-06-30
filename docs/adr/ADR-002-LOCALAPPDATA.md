# ADR-002: Dados do Usuário em %LOCALAPPDATA%

**Data**: 2024-01-15

## Contexto
O instalador do Windows instala em `Program Files` (read-only). Dados devem ser graváveis.

## Decisão
Banco de dados e config do usuário em `%LOCALAPPDATA%\CentralGestao\`.

## Consequências
- Dados sobrevivem à desinstalação
- Múltiplos usuários no mesmo PC têm dados isolados
