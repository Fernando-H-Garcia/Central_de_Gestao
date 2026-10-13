# ADR-007: Migrations SQL Versionadas

**Data**: 2024-01-15
**Status**: Vigente

> **Nota de revisão (2026-10):** registro escrito em 2024. Ver
> [`docs/README.md`](../README.md) sobre a política de datas.

## Contexto
Schema do banco evolui com o tempo. Necessário controle de versão.

## Decisão
Migrations SQL numeradas (`001_`, `002_`, ...), executadas em ordem na
inicialização, a partir de `database/migrations/`.

## Consequências
- Schema sempre atualizado na inicialização
- `schema_version` guarda a versão aplicada
- Rollback é manual (restaurar backup)

## Estado atual (2026-10-13)

| Métrica | Valor |
|---|---|
| Arquivos em `database/migrations/` | **25** |
| `schema_version` no banco | **26** |

**Arquivos ≠ versão do schema.** O número salta quando uma migration entrega
mais de uma versão (por exemplo, uma que adiciona duas features e registra
ambas). Documentos antigos diziam "20 migrations" — está desatualizado.

## Regra prática
- Para consultar a versão real: `SELECT MAX(version) FROM schema_version`
- Para contar arquivos: `len(list(Path('database/migrations').glob('*.sql')))`
- Nunca conte arquivos para decidir se o schema está em dia.