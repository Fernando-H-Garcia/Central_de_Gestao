# ADR-001: Uso do SQLite como Banco de Dados

**Data**: 2024-01-15

## Contexto
Necessidade de um banco de dados local, embarcado, sem necessidade de servidor.

## Decisão
SQLite é o banco oficial. Migrations versionadas em `database/migrations/`.

## Consequências
- Dados ficam em arquivo único (`brain.db`)
- Backup simples (cópia do arquivo)
- Sem concorrência multi-usuário
