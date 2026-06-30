# ADR-007: Migrations SQL Versionadas

**Data**: 2024-01-15

## Contexto
Schema do banco evolui com o tempo. Necessário controle de versão.

## Decisão
Migrations SQL numeradas (001_, 002_, ...). Executadas em ordem na inicialização.

## Consequências
- Schema sempre atualizado
- Rollback manual se necessário
- 20 migrations até o momento
